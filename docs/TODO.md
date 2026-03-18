# 开发路线图 TODO

> 目标：学术研究 Agent — 文献上传 → 多文档检索问答 → 对比分析 → 辅助写作全流程 AI 助理
>
> 参考技术方案：[tech-spec.md](./tech-spec.md)

---

## 当前状态

- [x] 项目骨架搭建（monorepo）
- [x] 后端 FastAPI 框架 + uv 环境
- [x] 前端 Next.js 14 + shadcn/ui
- [x] Docker Compose 配置
- [x] Git 仓库初始化

---

## Phase 1 — 核心链路（优先级最高）

> 目标：跑通「上传文档 → RAG 问答」完整链路

### 后端

- [ ] 补充 AI 依赖：`langchain langchain-openai qdrant-client openai`
- [ ] `app/services/doc_service.py` — 调用 2markdown 解析 PDF/Word → Markdown
- [ ] `app/repositories/vector_repo.py` — Qdrant 向量存取（连接远程 Qdrant）
- [ ] `app/services/rag_service.py` — 文本分块 + Embedding + 检索
- [ ] 完善 `POST /api/papers/upload` — 上传 → 解析 → 分块 → 存 Qdrant
- [ ] 完善 `GET /api/papers` — 从 DB/内存返回论文列表
- [ ] 完善 `POST /api/chat` — 单文档 RAG 问答，SSE 流式输出
- [ ] `app/config.py` 补充 Qdrant / 2markdown 配置项

### 前端

- [ ] 文档上传页 `app/papers/page.tsx` — 拖拽上传 + 论文列表
- [ ] 对话页 `app/chat/page.tsx` — 流式消息渲染
- [ ] `components/papers/UploadDropzone.tsx`
- [ ] `components/chat/MessageList.tsx` + `StreamingMessage.tsx`
- [ ] 联调：上传文档 → 对话问答 E2E 跑通

---

## Phase 2 — Agent 功能

> 目标：多文档对比 + LangGraph Agent 编排

### 后端

- [ ] `app/core/graph.py` — LangGraph StateGraph 定义（ResearchState）
- [ ] `app/core/agents/research_agent.py` — 检索规划 Agent
- [ ] `app/core/agents/writer_agent.py` — 内容生成 Agent
- [ ] `app/core/agents/review_agent.py` — 质量评审 + 反思循环
- [ ] `app/core/tools/web_search.py` — Tavily Web 搜索 Tool
- [ ] 完善 `POST /api/analyze` — 多文档对比分析（跨 Qdrant collection 检索）

### 前端

- [ ] 多文档选择器 `components/papers/PaperSelector.tsx`
- [ ] 对比分析页 `app/analyze/page.tsx`
- [ ] Mermaid 图渲染组件

---

## Phase 3 — 写作辅助

> 目标：LaTeX / Mermaid 生成，完善 Agent 工具链

- [ ] `app/core/tools/latex_writer.py` — LaTeX 片段生成
- [ ] `app/core/tools/mermaid_gen.py` — Mermaid 图生成
- [ ] `POST /api/export/latex` 接口
- [ ] `POST /api/export/mermaid` 接口
- [ ] 前端导出按钮 + 预览

---

## Phase 4 — 加分项（后续迭代）

- [ ] MCP Server 暴露（`mcp_server.py`，供 Claude Desktop / Cursor 调用）
- [ ] A2A 协议集成（Sub-Agent 微服务化）
- [ ] 用户认证（JWT）
- [ ] PostgreSQL 持久化替代内存存储
- [ ] CI/CD（GitHub Actions → Docker build → 部署）

---

## 技术决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-03 | Monorepo（前后端同仓库） | 个人项目，文档/Docker 共享方便 |
| 2026-03 | uv 管理 Python 环境 | 速度快，锁文件规范 |
| 2026-03 | 向量库/关系库先用远程 | 避免本地资源占用，加速开发迭代 |
| 2026-03 | Next.js standalone 模式 | Docker 镜像更小，生产友好 |
