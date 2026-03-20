import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.graph import research_graph
from app.models.request import AnalyzeRequest
from app.repositories import analysis_repo, paper_repo

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
    initial_state = {
        "query": req.query,
        "paper_ids": req.paper_ids,
        "sub_queries": [],
        "context_chunks": [],
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

    # 持久化分析结果
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
