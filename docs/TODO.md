# 开发路线图 TODO

> 目标：学术研究 Agent — 文献上传 → 多文档检索问答 → 对比分析 → 辅助写作全流程 AI 助理
>
> 参考技术方案：[tech-spec.md](./tech-spec.md) | 文档解析方案：[doc-parsing.md](./doc-parsing.md)

---

## 当前状态

- [x] 项目骨架搭建（monorepo）
- [x] 后端 FastAPI 框架 + uv 环境
- [x] 前端 Next.js 14 + shadcn/ui
- [x] Docker Compose（应用 + 基础设施分离）
- [x] Git 仓库初始化并推送

---

## Phase 1 — 核心链路 ✅ 后端完成

### 后端

- [x] 依赖安装：`markitdown pymupdf4llm qdrant-client langchain langchain-openai`
- [x] `app/models/` — Paper、ChatRequest、AnalyzeRequest、响应模型
- [x] `app/repositories/paper_store.py` — 内存 Paper 元数据存储（Phase 4 替换为 PostgreSQL）
- [x] `app/repositories/vector_repo.py` — Qdrant 操作（collection per paper）
- [x] `app/services/doc_service.py` — Word（markitdown）+ PDF（pymupdf4llm）解析
- [x] `app/services/rag_service.py` — 分块 + OpenAI Embedding + Qdrant 检索
- [x] `POST /api/papers/upload` — 上传 → BackgroundTask 异步处理
- [x] `GET /api/papers` — 论文列表
- [x] `GET /api/papers/{id}/status` — 处理状态轮询
- [x] `DELETE /api/papers/{id}` — 删除论文 + Qdrant collection
- [x] `POST /api/chat` — 单文档 RAG 问答，SSE 流式输出
- [x] `POST /api/analyze` — 多文档对比分析，SSE 流式输出

### 前端 ✅ 完成

- [x] 文档上传页 `app/papers/page.tsx` — 拖拽上传 + 论文列表 + 状态轮询
- [x] 对话页 `app/chat/page.tsx` — 流式消息渲染
- [x] `components/papers/UploadDropzone.tsx` — 拖拽 + 点击上传，50MB 限制
- [x] `components/papers/PaperCard.tsx` — 状态展示，processing 每 2s 轮询
- [x] `components/chat/MessageList.tsx` — 消息气泡 + 流式光标动画
- [x] `components/chat/ChatInput.tsx` — Enter 发送，Shift+Enter 换行

### E2E 联调（待完成）

> 前提：配置好 `backend/.env`（OPENAI_API_KEY、QDRANT_URL），启动 Qdrant

- [ ] `GET /health` 返回 `{"status": "ok"}`
- [ ] 上传 PDF → 返回 `{ paper_id, status: "processing" }`
- [ ] 轮询 status → 最终变为 `"ready"`，前端卡片状态自动更新
- [ ] 点选论文 → 对话页提问 → 流式返回答案
- [ ] 删除论文 → Qdrant collection 清除，卡片消失

---

## Phase 2 — Agent 功能

> 目标：多文档对比 + LangGraph Agent 编排

### 后端

- [ ] `app/core/graph.py` — LangGraph StateGraph 定义（ResearchState）
- [ ] `app/core/agents/research_agent.py` — 检索规划 Agent
- [ ] `app/core/agents/writer_agent.py` — 内容生成 Agent
- [ ] `app/core/agents/review_agent.py` — 质量评审 + 反思循环
- [ ] `app/core/tools/web_search.py` — Tavily Web 搜索 Tool
- [ ] `/api/analyze` 升级为 LangGraph 多 Agent 流程

### 前端

- [ ] 多文档选择器 `components/papers/PaperSelector.tsx`
- [ ] 对比分析页 `app/analyze/page.tsx`
- [ ] Mermaid 图渲染组件

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
- [ ] PostgreSQL 替代内存存储（`paper_store.py` → SQLAlchemy）
- [ ] Redis 缓存 Embedding 结果（避免重复计算）
- [ ] A2A 协议集成（Sub-Agent 微服务化）
- [ ] CI/CD（GitHub Actions → Docker build → 部署）
- [ ] 用户认证（JWT）

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
| 2026-03 | 内存存储 Paper 元数据 | Phase 1 够用，Phase 4 迁移 PostgreSQL |
