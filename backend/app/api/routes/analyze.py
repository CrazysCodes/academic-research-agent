"""
分析路由：LangGraph 多 Agent 分析 + 报告优化 + 历史 CRUD。
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import HumanMessage, SystemMessage

from app.api.deps import get_db_session
from app.core.graph import research_graph
from app.core.llm import create_chat_llm
from app.core.nodes.query_rewrite import rewrite_analyze_query
from app.models.request import AnalyzeRequest, RefineRequest
from app.repositories import analysis_repo, paper_repo
from app.repositories import vector_repo
from app.services import rag_service

logger = logging.getLogger(__name__)

router = APIRouter()

_NODE_LABELS: dict[str, str] = {
    "planner": "规划查询",
    "retriever": "检索文献",
    "writer": "撰写报告",
    "reviewer": "质量评审",
}

_PASS_SCORE = 7
_MAX_ITERATIONS = 2
_PREVIEW_LENGTH = 200
_PREVIEW_COUNT = 5


def _build_node_output_payload(name: str, output: dict, *, iterations: int = 0) -> dict:
    """将节点原始输出裁剪为前端友好的 payload。"""
    if name == "planner":
        return {"sub_queries": output.get("sub_queries", [])}
    if name == "retriever":
        chunks = output.get("context_chunks", [])
        return {
            "chunk_count": len(chunks),
            "previews": [c[:_PREVIEW_LENGTH] for c in chunks[:_PREVIEW_COUNT]],
        }
    if name == "writer":
        iters = output.get("iterations", 1)
        return {"iterations": iters, "is_revision": iters > 1}
    if name == "reviewer":
        score = output.get("score", 0)
        return {
            "score": score,
            "feedback": output.get("feedback", ""),
            "will_revise": score < _PASS_SCORE and iterations < _MAX_ITERATIONS,
        }
    return {}


async def _stream_agent(req: AnalyzeRequest, db: AsyncSession):
    """执行完整 LangGraph Agent 管线：Planner → Retriever → Writer → Reviewer。"""
    logger.info("开始多 Agent 分析，paper_ids=%s，query=%s", req.paper_ids, req.query[:80])
    rewrite = await rewrite_analyze_query(req.query)
    agent_query = rewrite.rewritten_query

    # 全文模式：预加载所有选中论文的全部文本块，跳过 RAG 向量检索
    # 按论文交替取块（轮询），确保多篇论文均匀覆盖
    # 限制总字符数在 _MAX_CONTEXT_CHARS 内，防止超出 LLM 上下文窗口
    _MAX_CONTEXT_CHARS = 60_000  # 约 15K-20K tokens，主流 LLM 均可处理
    per_paper_chunks: list[list[str]] = []
    for paper_id in req.paper_ids:
        chunks = vector_repo.get_all_chunks(paper_id)
        per_paper_chunks.append([c["text"] for c in chunks])

    # 轮询交替合并，保证各论文内容均衡
    all_chunks: list[str] = []
    total_chars = 0
    max_len = max((len(c) for c in per_paper_chunks), default=0)
    for i in range(max_len):
        for paper_chunks in per_paper_chunks:
            if i < len(paper_chunks):
                chunk_text = paper_chunks[i]
                if total_chars + len(chunk_text) > _MAX_CONTEXT_CHARS:
                    break
                all_chunks.append(chunk_text)
                total_chars += len(chunk_text)
        if total_chars >= _MAX_CONTEXT_CHARS:
            break

    logger.info(
        "全文模式：共加载 %d 个文本块（来自 %d 篇论文），总字符数=%d（上限 %d）",
        len(all_chunks), len(req.paper_ids), total_chars, _MAX_CONTEXT_CHARS,
    )

    initial_state = {
        "query": agent_query,
        "paper_ids": req.paper_ids,
        "sub_queries": [],
        "context_chunks": all_chunks,  # 预填充全文，RetrieverNode 将跳过 RAG
        "draft": "",
        "score": 0,
        "feedback": "",
        "iterations": 0,
    }

    last_iterations = 0
    final_draft = ""
    final_score = 0
    collected_outputs: dict[str, dict] = {}

    async for event in research_graph.astream_events(initial_state, version="v2"):
        kind = event["event"]
        name = event.get("name", "")
        metadata = event.get("metadata", {})

        # 节点开始：推送进度事件
        if kind == "on_chain_start" and name in _NODE_LABELS:
            yield f"data: {json.dumps({'event': 'node', 'name': name, 'label': _NODE_LABELS[name]})}\n\n"

        # 节点结束：推送节点输出 + 收集用于持久化
        elif kind == "on_chain_end" and name in _NODE_LABELS:
            output = event["data"].get("output", {})
            if name == "writer":
                last_iterations = output.get("iterations", last_iterations)
                final_draft = output.get("draft", final_draft)
            if name == "reviewer":
                final_score = output.get("score", 0)
            payload = _build_node_output_payload(name, output, iterations=last_iterations)
            # 收集时按 name_iteration 区分修订轮次
            key = f"{name}_{last_iterations}" if name in ("writer", "reviewer") else name
            collected_outputs[key] = payload
            yield f"data: {json.dumps({'event': 'node_output', 'name': name, 'data': payload})}\n\n"

        # WriterNode 内 LLM 流式 token：推送 delta 事件
        elif kind == "on_chat_model_stream" and metadata.get("langgraph_node") == "writer":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                yield f"data: {json.dumps({'event': 'delta', 'content': chunk.content})}\n\n"

    # 持久化分析结果到数据库
    logger.info("Agent 分析完成，score=%d，iterations=%d，正在持久化", final_score, last_iterations)
    analysis = await analysis_repo.create(
        db,
        query=req.query,
        mode=req.mode,
        paper_ids=req.paper_ids,
        result=final_draft,
        score=final_score,
        iterations=last_iterations,
        node_outputs=collected_outputs,
    )

    yield f"data: {json.dumps({'event': 'done', 'analysis_id': analysis.id})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("")
async def analyze(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """多文档分析端点：校验论文 → 执行 LangGraph Agent 管线 → SSE 流式输出。"""
    if not req.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper must be selected")

    for paper_id in req.paper_ids:
        paper = await paper_repo.get(db, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        if paper.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Paper '{paper.title}' is not ready (status: {paper.status})",
            )

    return StreamingResponse(
        _stream_agent(req, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ────────────── 报告优化（对话式修订） ──────────────

_REFINE_SYSTEM_PROMPT = """你是一位学术研究报告优化助手。

## 论文原文片段（RAG 检索结果）
{context}

## 当前报告
{report}

## 用户修改要求
{instruction}

请基于论文原文片段和当前报告，按照用户的修改要求输出完整的修订后报告（Markdown 格式）。
- 保留用户未要求修改的内容
- 引用论文原文时尽量准确
- 使用与原报告相同的语言"""

async def _stream_refine(analysis_id: str, instruction: str, db: AsyncSession):
    """
    报告优化流程：
    1. 从 DB 加载分析记录（报告 + 关联的 paper_ids）
    2. 加载论文全文（全文模式，不用 RAG）
    3. 将全文内容 + 当前报告 + 用户指令一起喂给 LLM
    4. 流式输出修订后的报告
    5. 持久化更新后的报告和优化记录
    """
    analysis = await analysis_repo.get(db, analysis_id)
    if not analysis:
        logger.warning("优化失败：分析记录 %s 不存在", analysis_id)
        yield f"data: {json.dumps({'error': 'Analysis not found'})}\n\n"
        return

    # 获取关联的论文 ID 列表
    paper_ids = [link.paper_id for link in analysis.paper_links]
    logger.info(
        "开始报告优化，analysis_id=%s，paper_ids=%s，instruction=%s",
        analysis_id, paper_ids, instruction[:80],
    )

    # 全文模式：加载所有关联论文的全部文本块，限制总字符数
    _MAX_REFINE_CHARS = 40_000  # 优化时保留更多空间给当前报告
    context_chunks: list[str] = []
    if paper_ids:
        try:
            total_chars = 0
            for paper_id in paper_ids:
                chunks = vector_repo.get_all_chunks(paper_id)
                for c in chunks:
                    if total_chars + len(c["text"]) > _MAX_REFINE_CHARS:
                        break
                    context_chunks.append(c["text"])
                    total_chars += len(c["text"])
                if total_chars >= _MAX_REFINE_CHARS:
                    break
            logger.info("全文模式：共加载 %d 个文本块（来自 %d 篇论文），总字符数=%d", len(context_chunks), len(paper_ids), total_chars)
        except Exception as e:
            logger.warning("全文加载失败，将仅基于报告内容优化: %s", e)

    # 拼接检索到的论文原文片段
    context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "（未检索到相关论文片段）"

    # 构造 LLM 消息
    llm = create_chat_llm(streaming=True)
    system_prompt = _REFINE_SYSTEM_PROMPT.format(
        context=context_text,
        report=analysis.result,
        instruction=instruction,
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=instruction)]

    # [DEBUG] 打印完整 LLM 输入，便于排查上下文问题（确认后删除）
    logger.info(
        "[DEBUG][Refine] 发送给 LLM 的完整输入:\n"
        "=== SYSTEM ===\n%s\n"
        "=== HUMAN ===\n%s",
        system_prompt,
        instruction,
    )

    # 流式输出修订后的报告
    new_result = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            new_result += chunk.content
            yield f"data: {json.dumps({'delta': chunk.content})}\n\n"

    # 持久化：更新报告内容 + 追加优化对话记录
    logger.info("报告优化完成，正在持久化，新报告长度=%d", len(new_result))
    await analysis_repo.append_refinement(
        db,
        analysis_id,
        new_result,
        [
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": "已根据要求更新报告。"},
        ],
    )

    yield "data: [DONE]\n\n"


@router.post("/{analysis_id}/refine")
async def refine_analysis(
    analysis_id: str,
    req: RefineRequest,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """报告优化端点：基于论文原文 + 当前报告 + 用户指令，流式输出修订报告。"""
    analysis = await analysis_repo.get(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    logger.info("收到报告优化请求，analysis_id=%s", analysis_id)
    return StreamingResponse(
        _stream_refine(analysis_id, req.instruction, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ────────────── 分析历史 CRUD ──────────────


def _format_analysis(a) -> dict:
    return {
        "id": a.id,
        "query": a.query,
        "mode": a.mode,
        "paper_ids": [link.paper_id for link in a.paper_links],
        "result": a.result,
        "score": a.score,
        "iterations": a.iterations,
        "node_outputs": a.node_outputs,
        "refinements": a.refinements or [],
        "created_at": a.created_at,
    }


@router.get("/history")
async def list_analyses(db: AsyncSession = Depends(get_db_session)):
    rows = await analysis_repo.list_all(db)
    return [_format_analysis(a) for a in rows]


@router.get("/history/{analysis_id}")
async def get_analysis(analysis_id: str, db: AsyncSession = Depends(get_db_session)):
    a = await analysis_repo.get(db, analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _format_analysis(a)


@router.delete("/history/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: str, db: AsyncSession = Depends(get_db_session)):
    deleted = await analysis_repo.delete(db, analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found")
