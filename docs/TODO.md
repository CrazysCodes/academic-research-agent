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
- [x] `components/chat/ChatInput.tsx` — Enter 发送，Shift+Enter 换行，IME 中文输入法兼容
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

> 目标：多文档对比 + LangGraph Agent 编排 + 分析历史持久化 + 对话式优化报告

### Agent 图设计（LangGraph StateGraph）

```
用户输入
  → PlannerNode    拆解问题为 3~5 个子查询（Function Calling 强约束输出 JSON）
  → RetrieverNode  全文模式：预加载论文全文（≤60K字符），跳过 RAG；降级时走向量检索
  → WriterNode     生成结构化报告 + 可选 Tavily Web Search 补充外部知识
  → ReviewerNode   质量评分(0-10)，< 7分打回 WriterNode 重写（最多2轮）
  → Done           持久化到 DB + 推送最终报告
```

### 后端

- [x] `app/core/state.py` — ResearchState TypedDict（query, paper_ids, sub_queries, context_chunks, draft, score, feedback, iterations）
- [x] `app/core/nodes/planner.py` — Function Calling 强约束 → parse_json_markdown fallback → retry with error feedback
- [x] `app/core/nodes/retriever.py` — 全文模式透传（context_chunks 已预填充时跳过 RAG）；降级 RAG 兜底
- [x] `app/core/nodes/writer.py` — 初次写作 + Tavily Web Search 补充；修订模式接收 reviewer feedback
- [x] `app/core/nodes/reviewer.py` — Function Calling 强约束评分 → parse_json_markdown fallback → retry
- [x] `app/core/graph.py` — StateGraph 组装，条件边（score < 7 → writer，否则 → done）
- [x] `app/core/tools/web_search.py` — Tavily 搜索 Tool（可选，需 TAVILY_API_KEY）
- [x] `app/core/llm.py` — `create_structured_llm()` 工厂，封装 `with_structured_output(method="function_calling")`
- [x] `app/config.py` 新增 `tavily_api_key`
- [x] `app/main.py` — `logging.basicConfig(level=INFO)` 全局日志配置
- [x] 全文模式（`_stream_agent`）：轮询交替加载各论文全文块，限制 60K 字符防超出上下文窗口
- [x] `/api/analyze` 升级：LangGraph `astream_events` → SSE（node / node_output / delta / done）
- [x] `app/db/models.py` — AnalysisORM（含 `refinements` JSON 列）+ AnalysisPaperORM
- [x] `app/repositories/analysis_repo.py` — 分析历史 CRUD + `append_refinement()`
- [x] `POST /api/analyze/{id}/refine` — 报告对话式优化端点（全文模式 + SSE 流式输出）
- [x] `GET /api/analyze/history` — 历史列表
- [x] `GET /api/analyze/history/{id}` — 历史详情（含 refinements 记录）
- [x] `DELETE /api/analyze/history/{id}` — 删除历史

### SSE 事件协议

```json
{ "event": "node",        "name": "planner", "label": "规划查询" }
{ "event": "node_output", "name": "planner", "data": {"sub_queries": [...]} }
{ "event": "delta",       "content": "..." }
{ "event": "done",        "analysis_id": "uuid" }
```

### 前端

- [x] `app/analyze/page.tsx` — 分析页完整交互：
  - 分析历史侧边栏（加载/删除/新建）
  - 首次分析后自动隐藏输入表单，显示查询摘要卡片
  - 结果区可切换论文选择 pill（已选高亮 + 点击切换）
  - 对话式优化区（ChatInput + 消息气泡 + 流式更新）
  - 加载历史时恢复选中论文 + 恢复优化对话记录
  - Textarea Enter 键 IME 中文输入法兼容
- [x] `components/analyze/AgentProgress.tsx` — 垂直时间线 + 可折叠节点详情面板
- [x] `components/layout/NavLinks.tsx` — Tab 顺序：问答 → 分析 → 文献库
- [x] `components/layout/AppInitializer.tsx` — 全局初始化，应用启动时自动加载论文列表
- [x] `app/layout.tsx` — 挂载 AppInitializer，确保各页面均可见已上传文献
- [x] `lib/api.ts` — `streamAnalyze()` + `streamRefineAnalysis()` + 分析历史 API
- [x] `lib/store.ts` — 新增 `setSelectedPaperIds()` action
- [x] `types/index.ts` — AgentSSEEvent、NodeStep、Analysis（含 refinements）等类型
- [x] 问答页文献选择 pill 移至输入框上方（底部 footer 内）

---

## Phase 3 — RAG 增强 + 报告增强与导出 🚧 规划中

> 目标：RAG 管线优化 + 让分析报告更专业可导出 + 引入图表和写作辅助

### 3.0 RAG 管线增强

> 当前：用户问题直接 embedding 检索，复杂/简短问题召回差。
> 目标：Query Rewrite → 改写成高质量检索问题再检索。

- [ ] `app/core/nodes/query_rewrite.py` — QueryRewriteNode：LLM 将用户原始问题改写成更适合检索的形式
  - **analyze 管线**：改写成结构化分析问题（适合 Planner 多子查询）
  - **chat 管线**：Query Expansion / HyDE 改进召回（短问题→完整问题，或用猜测答案辅助检索）
- [ ] chat 管线：`POST /api/chat` 接入 QueryRewriteNode，rewrite 后再 RAG
- [ ] analyze 管线：`_stream_agent` 入口处加 query rewrite，预处理后再进 PlannerNode

### 3.1 报告导出

- [x] `GET /api/analyze/{id}/export/markdown` — 下载完整 Markdown 文件（含查询、文献列表、Agent 摘要、正文、优化历史）
- [x] PDF 导出：前端 `window.print()` + `@media print` CSS（零后端依赖）
- [x] 前端分析页导出工具栏（Markdown / PDF 两个按钮，有 analysis_id 时显示）

### 3.2 Mermaid 图表生成

- [x] `POST /api/analyze/{id}/diagram` — LLM 从报告内容生成 Mermaid 代码，支持 relationship / flowchart / timeline 三种类型
- [x] `components/analyze/MermaidDiagram.tsx` — 动态 import mermaid，useEffect 异步渲染 SVG，含错误状态
- [x] 前端分析页结果区下方「生成图表」卡片（三种类型按钮）

### 3.3 引用格式化

- [x] `POST /api/papers/{id}/citation` — LLM 从论文首页文本提取元数据，生成 APA / MLA / IEEE / BibTeX 格式引用
- [x] `components/papers/PaperCard.tsx` — 就绪论文新增「引用」下拉按钮，点击复制到剪贴板 + 勾号反馈

### 3.4 写作草稿辅助

- [x] `POST /api/analyze/{id}/draft-section` — SSE 流式生成章节草稿（摘要/引言/相关工作），基于分析报告 + 论文全文上下文
- [x] 前端对话优化区右上角「生成：摘要 / 引言 / 相关工作」快捷按钮，流式渲染到对话消息流

---

## Phase 4 — RAG 生产级 + Memory 系统

> 目标：把 RAG 从"玩具级"提升到"生产级"；加入跨会话长期记忆，实现真正的知识积累。
> 核心认知：编排器（LangGraph）是通用基础设施，本阶段重点是强化 RAG 质量和 Memory 体系。

### 4.1 混合检索（Hybrid Search）

- [ ] `rag_service.retrieve()` 改造：BM25 关键词检索 + 向量检索双路并行
- [ ] 分数加权融合（RRF 或线性加权），取 top-k
- [ ] 降级策略：某一路失败时另一路兜底

### 4.2 Re-ranker（Cross-Encoder 精排）

- [ ] 向量检索 top-20 → Cross-Encoder（bge-reranker-base）重排 → top-5
- [ ] reranker 服务可独立部署（本地模型或 API）
- [ ] 配置开关，可按需开启/关闭

### 4.3 Citation Grounding（引用溯源）

- [ ] LLM 生成回答时强制标注来源片段 `[Source: chunk_id, paper_title]`
- [ ] 前端消息渲染：引用片段高亮 + 点击跳转原文
- [ ] `GET /api/papers/{id}/chunks/{chunk_id}` 返回具体段落

### 4.4 跨会话 Memory（Long-Term KB）

- [ ] 论文上传时自动提取：标题、作者、年份、摘要、关键词，存入 PostgreSQL
- [ ] 新会话创建时自动关联相关历史论文（基于 embedding 相似度）
- [ ] 分析报告历史自动归档为可检索知识条目
- [ ] `GET /api/kb/search` — 语义搜索历史报告/论文摘要

### 4.5 会话摘要（Conversation Summarization）

- [ ] 消息数 > 20 或 token 估计 > 30K 时触发摘要
- [ ] 摘要替换对话历史进入 context，仅保留摘要 + 最近 N 条
- [ ] 摘要结果存入 DB，会话恢复时先读摘要

---

## Phase 5 — Tool 生态扩展 + 可观测性

> 目标：让 Agent 真正成为"全能助手"，不只是"分析师"；建立生产级可观测性。

### 5.1 MCP Server 暴露

- [ ] `app/mcp/server.py` — FastAPI → MCP 协议转换层
- [ ] 暴露工具：search_papers / analyze / chat / get_history
- [ ] 支持 Cursor / Claude Desktop 直接调用本项目 Agent

### 5.2 Code Interpreter

- [ ] 安全沙箱执行 Python 代码（` Pyodide` 或 `subprocess + timeout`）
- [ ] 分析报告时自动跑实验数据对比、生成统计图表
- [ ] 前端展示代码执行结果（表格 + matplotlib 图表）

### 5.3 意图识别（Intent Classification）

- [ ] 单一对话入口（取消 chat/analyze tab 区分）
- [ ] `IntentNode`：classify → {rag, analyze, writing, search_web, general}
- [ ] 多意图时并发路由，同时执行后合并结果
- [ ] 意图不明时默认 rag + analyze 并发

### 5.4 分布式追踪（Observability）

- [ ] 集成 LangSmith（可选，API Key 配置开关）
- [ ] 记录每次请求的：token 消耗、节点耗时、检索召回率
- [ ] 慢查询告警（单个节点 > 60s 或 总流程 > 5min）
- [ ] 每轮 Agent 调用写入审计表（`agent_audit_log`）

---

## Phase 6 — Multi-Agent 协作 + 自动优化

> 目标：从单 Agent 进化到 Agent 团队协作；Agent 具备自我反思和改进能力。

### 6.1 Multi-Agent 路由

- [ ] `RouterNode`：根据意图分发到专业 Agent
  - `ResearchAgent` — 分析、对比、方法论评估
  - `WritingAgent` — 写作辅助、章节草稿、引用格式化
  - `SearchAgent` — 外部检索、文献发现、arXiv 监控
- [ ] Agent 间通过 Graph State 共享上下文

### 6.2 Agent Self-Improvement

- [ ] 用户反馈收集（👍/👎 按钮）写入反馈表
- [ ] 根据反馈自动调整：检索权重、回答风格、评分标准
- [ ] RAG 检索结果评分闭环（用户点击引用的片段 = 高质量信号）

### 6.3 主动推送（Proactive Agent）

- [ ] 定期检查新上线的相关论文（arXiv API 监控）
- [ ] 用户上传新论文 → 自动触发相关历史分析通知
- [ ] 重大发现（论文引用关系变化）主动摘要推送

---

## Phase 7 — 工程化与部署

- [ ] Redis 缓存 Embedding 结果（避免重复计算同一片段）
- [ ] CI/CD（GitHub Actions → Docker build → 部署）
- [ ] 用户认证（JWT）
- [ ] A2A 协议集成（Sub-Agent 微服务化）

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
| 2026-03 | 分析用全文模式而非 RAG | RAG 分块太小（100+块/篇），LLM 获取信息严重不足；全文模式限 60K 字符均衡取块 |
| 2026-03 | LLM 结构化输出用 Function Calling | `with_structured_output(method="function_calling")` 代理层强约束，比 prompt JSON 指令可靠 10 倍 |
| 2026-03 | 解析兜底用 parse_json_markdown | LangChain 内置，自动剥 ```json 围栏，比手写正则更健壮；配合 retry 构成三层防线 |
