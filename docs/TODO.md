# 开发路线图 TODO

> 目标：学术研究 Agent — 文献上传 → 多文档检索问答 → 对比分析 → 辅助写作全流程 AI 助理
>
> 参考技术方案：[tech-spec.md](./tech-spec.md) | 文档解析方案：[doc-parsing.md](./doc-parsing.md) | 向量库&RAG调研：[research-vector-db-and-rag.md](./research-vector-db-and-rag.md)

---

## 当前状态

- [x] 项目骨架搭建（monorepo）
- [x] 后端 FastAPI 框架 + uv 环境
- [x] 前端 Next.js 14 + shadcn/ui
- [x] Docker Compose（应用 + 基础设施分离）
- [x] Git 仓库初始化并推送（monorepo → github.com/CrazysCodes/academic-research-agent）
- [x] 服务器 Qdrant 部署（115.190.79.5:6333，Docker infra 层）
- [x] 服务器 PostgreSQL 部署（docker-compose.infra.yml，5432 端口）
- [x] Paper 元数据持久化（SQLAlchemy 异步 + asyncpg + PostgreSQL）
- [x] 会话历史持久化（conversations / messages 表 + REST API）

---

## Phase 1 — 核心链路 ✅ 完成

### 后端

- [x] 依赖安装：`markitdown pymupdf4llm qdrant-client langchain langchain-openai sqlalchemy asyncpg`
- [x] `app/models/` — Paper、ChatRequest、AnalyzeRequest、响应模型
- [x] `app/db/models.py` — SQLAlchemy ORM 模型（PaperORM、ConversationORM、MessageORM）
- [x] `app/db/database.py` — 异步 engine + session factory + `init_db()`
- [x] `app/repositories/paper_repo.py` — 异步 DB Paper CRUD
- [x] `app/repositories/conversation_repo.py` — 会话 + 消息 CRUD
- [x] `app/repositories/vector_repo.py` — Qdrant 操作（collection per paper）+ `get_all_chunks()`
- [x] `app/services/doc_service.py` — Word（markitdown）+ PDF（pymupdf4llm）解析
- [x] `app/services/rag_service.py` — 分块 + OpenAI Embedding + Qdrant 检索
- [x] `POST /api/papers/upload` — 上传 → BackgroundTask 异步处理（写 DB）
- [x] `GET /api/papers` — 论文列表（DB）
- [x] `GET /api/papers/{id}` — 论文详情
- [x] `GET /api/papers/{id}/chunks` — 论文切块列表（from Qdrant）
- [x] `GET /api/papers/{id}/status` — 处理状态轮询
- [x] `DELETE /api/papers/{id}` — 删除论文 + Qdrant collection
- [x] `POST /api/chat` — RAG 问答 / 通用 LLM 模式（paper_ids 为空时降级），SSE 流式输出
- [x] `POST /api/analyze` — 多文档对比分析，SSE 流式输出
- [x] `GET/POST/DELETE/PATCH /api/conversations` — 会话历史 CRUD
- [x] `POST /api/conversations/{id}/messages` — 保存消息到会话
- [x] `GET/PATCH /api/settings` — 运行时模型切换
- [x] `app/core/llm.py` — LLM 工厂函数，统一 base_url 传递

### 前端 ✅ 完成

- [x] 文献库 `app/papers/page.tsx` — 拖拽上传 + 论文列表 + 状态轮询
- [x] 文献详情 `app/papers/[id]/page.tsx` — 切块列表 Tab + 文档原文 Tab（markdown 渲染）
- [x] 对话页 `app/chat/page.tsx` — 历史对话侧边栏 + 消息流式渲染 + 自动创建/保存会话
- [x] 设置页 `app/settings/page.tsx` — 模型选择 + 自定义 API 地址
- [x] `components/papers/UploadDropzone.tsx` — 拖拽 + 点击上传，50MB 限制
- [x] `components/papers/PaperCard.tsx` — 状态展示 + 详情入口（外链图标）
- [x] `components/chat/MessageList.tsx` — 美化消息气泡（AI/用户 avatar）+ 复制按钮 + 引导 empty state
- [x] `components/chat/ChatInput.tsx` — Enter 发送，Shift+Enter 换行
- [x] `components/layout/NavLinks.tsx` — 激活路由高亮（client 组件）
- [x] 无论文对话（通用 LLM 模式，不走 RAG，顶部显示模式提示）

### 后端增强

- [x] `OPENAI_BASE_URL` 支持任意 OpenAI 兼容 API（one-api/new-api/Azure）
- [x] Embedding 独立 API 地址/密钥配置
- [x] qdrant-client 1.17 API 适配（`search` → `query_points`）
- [x] 第三方 Embedding API 兼容（关闭 tiktoken、batch size 限制）
- [x] 流式输出 markdown 格式渲染（react-markdown + remark-gfm + Tailwind Typography）

### E2E 联调

**启动步骤：**

```bash
# 1. 启动基础设施（Qdrant + PostgreSQL）
docker compose -f docker-compose.infra.yml up -d

# 2. 配置并启动后端（backend/ 目录下）
cp .env.example .env   # 填入 OPENAI_API_KEY、QDRANT_URL、DATABASE_URL
UV_PROJECT_ENVIRONMENT=../venvs/backend uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs

# 3. 启动前端（frontend/ 目录下）
npm run dev
# → http://localhost:3000
```

**验收检查清单：**

- [x] `GET /health` 返回 `{"status": "ok"}`
- [x] 上传 PDF → 解析 → Qdrant 入库
- [x] 点选论文 → 对话页提问 → 流式返回答案（RAG 模式）
- [x] 未选论文 → 直接提问（通用 LLM 模式）
- [x] 对话自动保存到 PostgreSQL，刷新后侧边栏可见历史
- [x] Nav tab 激活高亮正确切换
- [x] 文献详情页查看切块内容和文档原文

**常见问题排查：**

| 现象 | 方向 |
|------|------|
| status 一直 processing | 后端日志查 BackgroundTask 报错 |
| chat 返回 404 "No relevant content" | Qdrant 是否连通，collection 是否创建 |
| 前端收不到 SSE | CORS 配置，`cors_origins` 是否含 `http://localhost:3000` |
| DB 连接失败 | PostgreSQL 是否启动，DATABASE_URL 是否正确 |

---

## Phase 2 — LangGraph 多 Agent 分析 ✅ 完成

> 目标：多文档对比 + LangGraph Agent 编排 + 分析历史持久化

### Agent 图设计（LangGraph StateGraph）

```
用户输入
  → PlannerNode    拆解问题为 3~5 个子查询
  → RetrieverNode  并发 RAG 检索，聚合 context chunks
  → WriterNode     生成结构化报告（摘要 / 对比 / 结论各节）
  → ReviewerNode   质量评分(0-10)，< 7分打回 WriterNode 重写（最多2轮）
  → Done           持久化到 DB + 推送最终报告
```

### 后端

- [x] `app/core/state.py` — ResearchState TypedDict（query, paper_ids, sub_queries, context_chunks, draft, score, feedback, iterations）
- [x] `app/core/nodes/planner.py` — PlannerNode：LLM 将问题拆解为子查询列表
- [x] `app/core/nodes/retriever.py` — RetrieverNode：并发调用 rag_service.retrieve()，合并去重
- [x] `app/core/nodes/writer.py` — WriterNode：按模板生成 Markdown 结构化报告，支持修订
- [x] `app/core/nodes/reviewer.py` — ReviewerNode：评分 + Tavily 外部搜索补充 + 条件打回
- [x] `app/core/graph.py` — StateGraph 组装，条件边（score < 7 → writer，否则 → done）
- [x] `app/core/tools/web_search.py` — Tavily 搜索 Tool（可选，需 TAVILY_API_KEY）
- [x] `app/config.py` 新增 `tavily_api_key`
- [x] `/api/analyze` 升级：LangGraph `astream_events` → SSE（node / node_output / delta / done）
- [x] `app/db/models.py` — AnalysisORM + AnalysisPaperORM（分析历史持久化）
- [x] `app/repositories/analysis_repo.py` — 分析历史 CRUD
- [x] `GET /api/analyze/history` — 历史列表
- [x] `GET /api/analyze/history/{id}` — 历史详情
- [x] `DELETE /api/analyze/history/{id}` — 删除历史
- [x] Embedding / Splitter 配置指纹检测，设置页改模型后无需重启

### SSE 事件协议

```json
{ "event": "node",        "name": "planner", "label": "规划查询" }
{ "event": "node_output", "name": "planner", "data": {"sub_queries": [...]} }
{ "event": "delta",       "content": "..." }
{ "event": "done",        "analysis_id": "uuid" }
```

### 前端

- [x] `app/analyze/page.tsx` — 分析页：文献选择 + 问题输入 + 历史侧边栏（加载/删除/新建）
- [x] `components/analyze/AgentProgress.tsx` — 垂直时间线 + 可折叠节点详情面板
- [x] `components/layout/NavLinks.tsx` — Tab 顺序调整：问答 → 文献库 → 分析
- [x] `lib/api.ts` — `streamAnalyze()` 支持 node/node_output/delta/done 事件 + 历史 API
- [x] `types/index.ts` — AgentSSEEvent、NodeStep、Analysis 等类型
- [x] 问答页就地选择文献（pill 选择器，无选中即通用问答）
- [x] 文献库页仅做上传/查看/删除，移除选择功能

---

## Phase 3 — 写作辅助

- [ ] `app/core/tools/latex_writer.py` — LaTeX 片段生成
- [ ] `app/core/tools/mermaid_gen.py` — Mermaid 图生成
- [ ] `POST /api/export/latex` 接口
- [ ] `POST /api/export/mermaid` 接口
- [ ] 前端导出按钮 + 预览

---

## Phase 4 — 加分项（后续迭代）

- [ ] MCP Server 暴露（`mcp_server.py`，供 Claude Desktop / Cursor 调用）
- [ ] Redis 缓存 Embedding 结果（避免重复计算）
- [ ] A2A 协议集成（Sub-Agent 微服务化）
- [ ] CI/CD（GitHub Actions → Docker build → 部署）
- [ ] 用户认证（JWT）

---

## Phase 5 — Java Spring AI 重写（Python demo 完成后）

> 技术路线决策：先 Python 完成完整 demo，再 1:1 用 Spring AI 重写，满足 Java 技术栈公司的面试需求。
> 详细分析见 [career-plan.md](./career-plan.md#语言技术路线决策2026-03-定稿)

### 核心对应关系

| Python | Java Spring AI |
|--------|----------------|
| `ChatOpenAI` | `ChatClient (OpenAI)` |
| `OpenAIEmbeddings` | `EmbeddingClient` |
| `Qdrant VectorStore` | `QdrantVectorStore` |
| `LangGraph StateGraph` | `Spring AI Advisor Chain + 手动状态机` |
| `FastAPI Router` | `Spring MVC @RestController` |
| `SQLAlchemy async` | `Spring Data JPA + R2DBC` |

### 任务清单

- [ ] 新建 `academic-research-agent-java` 仓库（或同仓库 `backend-java/` 子目录）
- [ ] Spring Boot 项目骨架（Spring AI + Web + Data JPA + PostgreSQL）
- [ ] Paper 上传 + 解析（Apache PDFBox / iText → markdown）
- [ ] Embedding + Qdrant 入库（Spring AI QdrantVectorStore）
- [ ] RAG 检索问答（ChatClient + EmbeddingClient + SSE 流式）
- [ ] 会话历史持久化（Spring Data JPA）
- [ ] Agent 功能迁移（Spring AI Advisor Chain）
- [ ] 前端保持不变（Next.js，后端 API 接口兼容）

---

## 技术决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-03 | Monorepo（前后端同仓库） | 个人项目，文档/Docker 共享方便 |
| 2026-03 | uv 管理 Python 环境 | 速度快，锁文件规范 |
| 2026-03 | 向量库先用远程 Qdrant Docker | 避免本地资源占用，加速开发迭代 |
| 2026-03 | Next.js standalone 模式 | Docker 镜像更小，生产友好 |
| 2026-03 | Word → markitdown | Microsoft 维护，底层 mammoth，LLM-ready 输出 |
| 2026-03 | PDF → pymupdf4llm | 比 marker 快 94x，学术 PDF 质量足够，无 GPU 依赖 |
| 2026-03 | PDF 解析用 BackgroundTasks | 避免 HTTP 超时，前端轮询 /status |
| 2026-03 | Paper 元数据用 PostgreSQL | 持久化，与会话历史统一数据源，重启不丢数据 |
| 2026-03 | 向量库选用 Qdrant | 中等规模最优解：性能好、生态全、部署简单。Vearch 社区弱/无BM25 |
| 2026-03 | 支持自定义 OpenAI Base URL | 兼容 one-api/new-api/Azure 等代理，不绑死官方 |
| 2026-03 | RAG + 长上下文互补策略 | RAG 做粗筛(成本低、引用溯源)，长上下文做精读(深度推理) |
| 2026-03 | SQLAlchemy async + asyncpg | 与 FastAPI async 生态一致，PostgreSQL 异步驱动性能好 |
| 2026-03 | Python 先行，Java 后跟 | LangGraph 无 Java 对等品；demo 完成后用 Spring AI 1:1 重写供 Java 岗面试 |
