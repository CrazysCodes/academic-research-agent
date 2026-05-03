# 学术研究 Agent — 前后端技术方案

> 基于 [career-plan.md](./career-plan.md) 整理，覆盖架构设计、目录结构、核心模块、数据流、部署方案。

---

## 1. 项目定位

**一句话**：帮助研究者完成从文献上传 → 多文档检索问答 → 对比分析 → 辅助写作的全流程 AI 助理。

**核心技术亮点（对齐 AI 应用研发 JD）**：
- RAG 多文档检索（Qdrant 向量库 + 混合检索）
- LangGraph 多 Agent 编排（检索 / 写作 / 评审 Sub-Agent）
- MCP Server 暴露（可供 Claude Desktop / Cursor 直接调用）
- markitdown + pymupdf4llm 文档解析（PDF/Word → Markdown，体现工程复用意识）

---

## 2. 技术栈总览

| 层次 | 技术选型 | 说明 |
|------|----------|------|
| 前端 UI | Next.js 16 + React 19 + TypeScript | App Router |
| 前端样式 | Tailwind CSS + shadcn/ui | 快速构建专业 UI |
| 前端状态 | Zustand | 轻量全局状态 |
| 前端数据 | SWR | 流式响应 + 缓存 |
| 后端框架 | FastAPI (Python 3.11+) | async，AI 应用事实标准 |
| 数据校验 | Pydantic v2 | 请求/响应模型 + 自动 OpenAPI |
| AI 编排 | LangChain + LangGraph | Agent 编排 + Tool 调用 |
| 向量库 | Qdrant | 高性能向量检索 |
| 关系库 | PostgreSQL + SQLAlchemy | 元数据持久化 |
| 缓存/队列 | Redis | 任务状态 + 响应缓存 |
| 文档解析 | markitdown + pymupdf4llm | PDF/Word → Markdown |
| 容器化 | Docker Compose | 一键启动所有服务 |

---

## 3. 系统整体架构

> 架构图：[system-architecture.drawio](./images/system-architecture.drawio)（用 draw.io 打开）

![系统整体架构](./images/system-architecture.drawio.png)

```
Browser
  │  HTTP
  ▼
Next.js (BFF / API Routes)
  │  HTTP/REST
  ▼
FastAPI 后端
  ├── API 路由层
  ├── Service 层
  ├── Core AI 层 (LangGraph)
  │     ├── ResearchAgent
  │     ├── WriterAgent
  │     └── ReviewAgent
  └── Repository 层
        ├── PostgreSQL
        └── Qdrant

外部服务：LLM API / Embedding API / Web Search
```

---

## 4. 后端分层架构

> 分层图：[fastapi-layered-architecture.drawio](./images/fastapi-layered-architecture.drawio)

![FastAPI 分层架构](./images/fastapi-layered-architecture.drawio.png)

### 4.1 目录结构

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── papers.py       # 文档上传、列表、删除
│   │   │   ├── chat.py         # 对话问答
│   │   │   ├── analyze.py      # 多文档对比分析
│   │   │   └── export.py       # LaTeX / Mermaid 导出
│   │   └── deps.py             # 依赖注入（DB Session、Auth）
│   ├── services/
│   │   ├── rag_service.py      # RAG 检索 + 上下文注入
│   │   ├── agent_service.py    # Agent 编排调用
│   │   └── doc_service.py      # 文档解析（markitdown / pymupdf4llm）
│   ├── core/
│   │   ├── agents/
│   │   │   ├── research_agent.py   # 检索规划 Agent
│   │   │   ├── writer_agent.py     # LaTeX 写作 Agent
│   │   │   └── review_agent.py     # 质量评审 Agent
│   │   ├── tools/
│   │   │   ├── web_search.py       # Tavily Web 搜索
│   │   │   ├── mermaid_gen.py      # Mermaid 图生成
│   │   │   └── latex_writer.py     # LaTeX 片段生成
│   │   ├── retriever.py            # Qdrant 向量检索
│   │   └── graph.py                # LangGraph 流程定义
│   ├── models/
│   │   ├── request.py              # Pydantic 请求模型
│   │   └── response.py             # Pydantic 响应模型
│   ├── repositories/
│   │   ├── paper_repo.py           # PostgreSQL ORM 操作
│   │   └── vector_repo.py          # Qdrant 向量存取
│   ├── config.py                   # 环境变量读取（pydantic-settings）
│   └── main.py                     # FastAPI 入口
├── tests/
│   ├── test_rag.py
│   └── test_agents.py
├── Dockerfile
└── requirements.txt
```

### 4.2 各层职责对比（Java 对应关系）

| 层次 | FastAPI | Java Spring 对应 |
|------|---------|-----------------|
| 路由层 | `api/routes/*.py` | `@RestController` |
| 依赖注入 | `api/deps.py` | `@Autowired` / Spring DI |
| 业务逻辑 | `services/*.py` | `@Service` |
| AI 核心 | `core/` | 无直接对应（AI 专有） |
| 数据模型 | `models/` (Pydantic) | DTO / VO + Jackson |
| 数据访问 | `repositories/` | `@Repository` / Mapper |
| 配置管理 | `config.py` | `application.yml` |

### 4.3 Pydantic 模型示例

```python
# models/request.py
from pydantic import BaseModel
from typing import Literal, Optional

class AnalyzeRequest(BaseModel):
    paper_ids: list[str]
    query: str
    mode: Literal["single", "compare"] = "single"
    max_tokens: Optional[int] = 2000

class UploadRequest(BaseModel):
    title: str
    source_url: Optional[str] = None

# models/response.py
class AnalyzeResponse(BaseModel):
    answer: str
    sources: list[str]
    tokens_used: int
    mermaid_diagram: Optional[str] = None  # 如有生成

class PaperInfo(BaseModel):
    id: str
    title: str
    abstract: str
    created_at: str
    chunk_count: int
```

---

## 5. LangGraph Agent 编排

### 5.1 多 Agent 工作流

```
用户请求（Query）
    │
    ▼
QueryRewriteNode（查询改写） ← Phase 3 已接入
    │  改写后的问题
    ▼
PlannerNode（规划拆解）
    │  3~5 个子查询
    ▼
RetrieverNode（检索）
    │  全文模式（≤60K 字符）或 RAG 混合检索
    ▼
WriterNode（写作生成）
    │  草稿 + 可选 Web Search 补充
    ▼
ReviewNode（质量评审）
    │  评分 0-10，<7 打回 Writer 重写
    ▼
最终响应（流式输出）
```

### 5.2 Query Rewrite 的价值

Query Rewrite 是生产级 RAG 的第一道优化。常见技术：

| 技术 | 做法 | 适用场景 |
|------|------|---------|
| Query Expansion | 短问题扩展为完整问题 | "DETR效果" → "DETR模型在目标检测任务上的性能指标（mAP/FPS）如何？" |
| HyDE | LLM 先猜答案，用猜测去检索 | 猜测答案中包含的关键词能更好命中相关片段 |
| Step-back | 抽象化问题再检索 | 具体问题 → 通类问题 → 再回到具体 |
| Sub-question | 拆成多个独立问题分别检索再合并 | 复杂多跳问题 |

analyze 管线用 Query Expansion（改写成结构化分析问题）；chat 管线用 HyDE（改进召回率）。

### 5.2 LangGraph 状态定义

```python
# core/graph.py
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
import operator

class ResearchState(TypedDict):
    query: str
    paper_ids: list[str]
    retrieved_chunks: Annotated[list, operator.add]
    draft: str
    review_feedback: str
    final_answer: str
    iteration: int

def build_research_graph() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("research", research_node)
    graph.add_node("write", write_node)
    graph.add_node("review", review_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "write")
    graph.add_conditional_edges(
        "review",
        should_continue,          # 评审通过 → END，否则 → write
        {"continue": "write", "end": END}
    )
    return graph.compile()
```

### 5.3 Tools 定义

```python
# core/tools/web_search.py
from langchain_core.tools import tool

@tool
async def search_papers(query: str) -> str:
    """搜索学术论文，返回摘要列表"""
    results = await tavily_client.search(query, max_results=5)
    return format_results(results)

@tool
async def generate_mermaid(description: str) -> str:
    """根据描述生成 Mermaid 流程图代码"""
    prompt = f"生成 Mermaid 图：{description}"
    return await llm.ainvoke(prompt)
```

---

## 6. RAG 实现方案

### 6.1 文档处理流水线

```
PDF/Word 上传
     │
     ▼
markitdown / pymupdf4llm 解析 → Markdown 文本
     │
     ▼
文本分块（chunk_size=512, overlap=64）
     │
     ▼
Embedding（text-embedding-3-small，默认 1536 维）
     │
     ▼
Qdrant 存储（collection per paper）

[检索时]
用户 Query → Embedding → Qdrant 相似搜索
           + BM25 关键词搜索（混合检索）
           → Rerank → Top-K chunks → LLM
```

### 6.2 混合检索（Hybrid Search）

```
用户 Query
    ├── Dense 检索（Embedding → Qdrant 向量搜索）
    └── Sparse 检索（BM25 关键词 → Qdrant 全文检索）
           ↓
    分数加权融合（RRF 或线性加权）
           ↓
    Cross-Encoder Re-ranker（top-20 → top-5）
           ↓
    精排后 Top-K → LLM
```

BM25 用 Qdrant 的 `match` 查询实现，无需额外服务。Re-ranker 用 `bge-reranker-base` 模型（本地或 API）。

### 6.3 Citation Grounding

LLM 生成回答时强制要求标注来源片段：

```
回答正文
... DETR 采用 Transformer 架构 [Source: chunk_23, HF-D-FINE] ...

前端渲染：点击引用跳转到原文片段高亮显示
```

实现方式：在 prompt 里要求引用 chunk_id，retriever 返回结果时附带上 chunk_id 和 paper_title。

```python
# repositories/vector_repo.py
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

async def create_paper_collection(paper_id: str):
    client.create_collection(
        collection_name=f"paper_{paper_id}",
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )

async def search_similar_chunks(paper_ids: list[str], query_vector: list[float], top_k: int = 10):
    # 跨 collection 检索（多文档对比核心）
    results = []
    for paper_id in paper_ids:
        hits = client.search(
            collection_name=f"paper_{paper_id}",
            query_vector=query_vector,
            limit=top_k
        )
        results.extend(hits)
    return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
```

---

## 7. 前端技术方案

### 7.1 目录结构

```
frontend/
├── app/
│   ├── (auth)/
│   │   └── login/page.tsx
│   ├── papers/
│   │   ├── page.tsx            # 文档管理列表
│   │   └── [id]/page.tsx       # 论文详情 + 阅读
│   ├── chat/
│   │   └── page.tsx            # 对话问答界面
│   ├── analyze/
│   │   └── page.tsx            # 多文档对比分析
│   └── layout.tsx
├── components/
│   ├── chat/
│   │   ├── MessageList.tsx     # 消息列表（支持 Markdown）
│   │   ├── ChatInput.tsx       # 输入框 + 文件选择
│   │   └── StreamingMessage.tsx # 流式输出
│   ├── papers/
│   │   ├── PaperCard.tsx
│   │   ├── UploadDropzone.tsx
│   │   └── PaperSelector.tsx   # 多文档选择器
│   └── ui/                     # shadcn/ui 组件
├── lib/
│   ├── api.ts                  # API 调用封装
│   └── store.ts                # Zustand store
└── types/
    └── index.ts                # 共享类型定义
```

### 7.2 流式输出实现

```typescript
// lib/api.ts
export async function streamAnalyze(
  request: AnalyzeRequest,
  onChunk: (text: string) => void
) {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    // SSE 格式: "data: {...}\n\n"
    const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
    for (const line of lines) {
      const data = JSON.parse(line.slice(6));
      if (data.delta) onChunk(data.delta);
    }
  }
}
```

### 7.3 FastAPI 流式响应

```python
# api/routes/chat.py
from fastapi.responses import StreamingResponse
import json

@router.post("/chat")
async def chat_stream(req: ChatRequest):
    async def generate():
        async for chunk in agent_service.stream(req.query, req.paper_ids):
            yield f"data: {json.dumps({'delta': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 8. MCP Server（加分项）

```python
# mcp_server.py
from mcp.server import MCPServer

server = MCPServer(name="academic-research-agent")

@server.tool()
async def search_papers(query: str, top_k: int = 5) -> str:
    """在已上传的论文库中检索相关内容"""
    results = await rag_service.search(query, top_k)
    return format_as_markdown(results)

@server.tool()
async def analyze_papers(paper_ids: list[str], question: str) -> str:
    """对指定论文集合进行深度分析"""
    return await agent_service.analyze(paper_ids, question)

@server.tool()
async def compare_papers(paper_ids: list[str], aspect: str) -> str:
    """多维度对比多篇论文"""
    return await agent_service.compare(paper_ids, aspect)

if __name__ == "__main__":
    server.run()  # 供 Claude Desktop / Cursor 调用
```

---

## 9. Docker Compose 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/research_agent
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - qdrant
      - redis

  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=research_agent
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  qdrant_data:
  redis_data:
```

---

## 10. 功能开发优先级

> 完整 Phase 规划见 [TODO.md](./TODO.md)，以下为技术层面的架构演进总览。

### Phase 1 — 核心链路 ✅ 已完成

- [x] Docker Compose 环境搭建（PostgreSQL + Qdrant + Redis）
- [x] FastAPI 基础框架 + 项目目录结构
- [x] PDF/Word 上传 → markitdown / pymupdf4llm 解析 → 分块 → Embedding → Qdrant 存储
- [x] 单文档 RAG 问答（`/chat` 接口 + 流式输出）
- [x] Next.js 基础 UI（文档上传 + 对话界面）

### Phase 2 — LangGraph 多 Agent ✅ 已完成

- [x] LangGraph ResearchAgent + WriterAgent + ReviewAgent
- [x] 多文档对比分析（跨 collection 检索）
- [x] Web 搜索 Tool 集成（Tavily）
- [x] 前端多文档选择器 + 对比结果展示 + 分析历史持久化

### Phase 3 — RAG 增强 + 报告导出 🚧 部分完成

- [x] Query Rewrite / Expansion（RAG 前查询改写）
- [x] Markdown / PDF 报告导出
- [x] Mermaid 图表生成
- [x] 引用格式化（APA / MLA / IEEE / BibTeX）
- [x] 写作草稿辅助（摘要 / 引言 / 相关工作章节生成）

### Phase 4 — RAG 生产级 + Memory 系统

- [ ] 混合检索（BM25 + 向量检索融合）
- [ ] Re-ranker（Cross-Encoder 精排 top-20 → top-5）
- [ ] Citation Grounding（引用溯源，LLM 回答标注来源片段）
- [ ] 跨会话 Memory（论文元数据 KB + 分析报告归档检索）
- [ ] 会话摘要（长对话压缩防溢出）

### Phase 5 — Tool 生态扩展 + 可观测性

- [ ] MCP Server 暴露（Claude Desktop / Cursor 直接调用）
- [ ] Code Interpreter（安全沙箱执行 Python）
- [ ] 意图识别（单一对话入口，多意图并发路由）
- [ ] 分布式追踪（LangSmith / OpenTelemetry + Token 统计 + 慢查询告警）

### Phase 6 — Multi-Agent 协作 + 自动优化

- [ ] Multi-Agent 路由（ResearchAgent / WritingAgent / SearchAgent 分工）
- [ ] Agent Self-Improvement（用户反馈闭环 + RAG 质量评分）
- [ ] 主动推送（arXiv 监控 + 新论文通知）

### Phase 7 — 工程化与部署

- [ ] Redis 缓存 Embedding 结果
- [ ] CI/CD + Docker build 优化
- [ ] 用户认证（JWT）
- [ ] A2A 协议集成（Sub-Agent 微服务化）

---

## 11. 关键 API 接口设计

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/papers/upload` | 上传 PDF/Word 文档 |
| `GET` | `/api/papers` | 获取论文列表 |
| `DELETE` | `/api/papers/{id}` | 删除论文 |
| `POST` | `/api/chat` | 流式对话问答（SSE） |
| `POST` | `/api/analyze` | 多文档对比分析（SSE） |
| `POST` | `/api/export/latex` | 导出 LaTeX 片段 |
| `POST` | `/api/export/mermaid` | 生成 Mermaid 图 |
| `GET` | `/docs` | FastAPI 自动生成 OpenAPI 文档 |

---

## 12. 面试价值点总结

| 技术点 | 体现能力 | 级别 |
|--------|----------|------|
| LangGraph 多 Agent 编排（Planner/Retriever/Writer/Reviewer） | Agent 工程化设计，非简单 LLM 调用 | 核心亮点 |
| Function Calling 结构化输出（三层解析防线） | 处理 LLM 不可靠输出的工程经验 | 核心亮点 |
| 全文模式替代 RAG（60K 字符轮询取块） | 根据场景选择最优方案而非套用模板 | 核心亮点 |
| Qdrant + 混合检索 RAG（BM25 + 向量 + Re-ranker） | 生产级 RAG 管线认知 | 进阶 |
| Query Rewrite / HyDE / Sub-question | RAG 优化深度，认知领先初级候选人 | 进阶 |
| Citation Grounding（引用溯源） | 学术场景领域理解，细节意识 | 进阶 |
| 跨会话 Memory 系统 | 长期知识积累架构设计能力 | 进阶 |
| FastAPI 分层架构 + async ORM | 后端工程规范，类比 Java 体现迁移能力 | 基础 |
| 流式 SSE 输出 + 前端状态管理 | 全栈联调能力，用户体验意识 | 基础 |
| MCP Server 暴露 | 前沿 AI 生态认知（加分项） | 加分 |
| markitdown/pymupdf4llm 文档解析 + Docker Compose | 工程复用意识，完整项目可运行 | 基础 |
