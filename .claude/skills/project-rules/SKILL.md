---
name: project-rules
description: academic-research-agent 项目专属开发规范。包含项目结构、技术栈约定、TODO 同步规则、本地联调流程。
---

# academic-research-agent 项目规范

## 项目结构

```
academic-research-agent/          ← monorepo 根
├── backend/                       ← FastAPI 后端（独立 git 子目录）
│   ├── app/
│   │   ├── api/routes/            ← 路由层（只做请求/响应）
│   │   ├── services/              ← 业务逻辑层
│   │   ├── core/agents/ tools/    ← LangGraph Agent / Tool
│   │   ├── models/                ← Pydantic 请求/响应模型
│   │   ├── repositories/          ← Qdrant + 内存 PaperStore
│   │   ├── config.py              ← pydantic-settings 统一配置
│   │   └── main.py
│   └── pyproject.toml             ← uv 管理依赖
├── frontend/                      ← Next.js 前端
│   ├── app/                       ← App Router 页面
│   ├── components/chat/ papers/   ← 业务组件
│   ├── components/ui/             ← shadcn/ui 基础组件（不手改）
│   ├── lib/api.ts                 ← 所有后端请求封装
│   ├── lib/store.ts               ← Zustand 全局状态
│   └── types/index.ts             ← 与后端 Pydantic 模型对齐的 TS 类型
├── docs/                          ← 所有文档
│   ├── TODO.md                    ← 开发路线图（必须保持最新）
│   ├── tech-spec.md
│   └── images/                    ← drawio + 导出图片
├── docker-compose.yml             ← 前后端应用
├── docker-compose.infra.yml       ← 基础设施（Qdrant）
└── venvs/backend/                 ← Python 虚拟环境（不提交 git）
```

---

## 关键技术约定

### 后端运行

```bash
# 在 backend/ 目录下，始终带环境变量
UV_PROJECT_ENVIRONMENT=../venvs/backend uv run <command>
UV_PROJECT_ENVIRONMENT=../venvs/backend uv sync        # 安装/更新依赖
UV_PROJECT_ENVIRONMENT=../venvs/backend uv add <pkg>   # 新增依赖
UV_PROJECT_ENVIRONMENT=../venvs/backend uv run uvicorn app.main:app --reload
```

### 异步文档处理

- Word（`.docx`）→ `markitdown`（同步，快）
- PDF（`.pdf`）→ `pymupdf4llm`（同步，快，无 GPU）
- 处理统一用 `BackgroundTasks` 异步，前端轮询 `/api/papers/{id}/status`
- marker 仅作扫描件降级备选，不在默认依赖中

### Qdrant

- 每篇论文一个 collection：`paper_{paper_id}`
- Embedding：OpenAI `text-embedding-3-small`（1536 维）
- 分块：`RecursiveCharacterTextSplitter`，chunk_size=512，overlap=64

### 前端状态

- Zustand store 是唯一全局状态，SSR 组件不使用 store
- 流式 SSE 用 `fetch` + `ReadableStream`，不用 EventSource
- `types/index.ts` 类型与后端 Pydantic 模型保持一致

---

## TODO.md 同步规则

**每次完成开发任务后，必须同步更新 `docs/TODO.md`：**

- 完成的条目 → 改为 `[x]` 标记
- 新发现的任务 → 按 Phase 插入对应位置
- 不再需要的任务 → 直接删除，不保留
- 重大技术决策 → 追加到底部「技术决策记录」表格

---

## 本地联调流程（Phase 1）

### 前提

- `.env` 已配置（`OPENAI_API_KEY`、`QDRANT_URL`）
- Qdrant 已启动

### 启动步骤

```bash
# 1. 启动 Qdrant
docker compose -f docker-compose.infra.yml up -d

# 2. 启动后端（backend/ 目录下）
UV_PROJECT_ENVIRONMENT=../venvs/backend uv run uvicorn app.main:app --reload --port 8000
# → Swagger UI: http://localhost:8000/docs

# 3. 启动前端（frontend/ 目录下）
cp .env.local.example .env.local   # 首次
npm run dev
# → http://localhost:3000
```

### E2E 联调检查清单

- [ ] `GET /health` 返回 `{"status": "ok"}`
- [ ] 上传 PDF → 返回 `{ paper_id, status: "processing" }`
- [ ] 轮询 `GET /api/papers/{id}/status` → 最终变为 `"ready"`
- [ ] 前端文献库页面显示论文卡片，状态自动从「解析中」变「就绪」
- [ ] 点选论文卡片 → 进入对话页 → 提问 → 流式返回答案
- [ ] 删除论文 → Qdrant collection 清除，卡片消失

### 常见问题

| 现象 | 排查方向 |
|------|----------|
| status 一直 processing | 后端日志查 BackgroundTask 报错 |
| chat 返回 404 "No relevant content" | Qdrant 是否连通，collection 是否创建成功 |
| 前端收不到 SSE | 检查 CORS 配置，`cors_origins` 是否包含 `http://localhost:3000` |
| PDF 解析失败 | 检查 pymupdf4llm 是否正确安装，临时文件权限 |

---

## 如何使用本规范

- **新增依赖** → 用 `uv add`，不手改 `pyproject.toml`
- **新建后端文件** → 确认放对分层目录（routes / services / core / repositories / models）
- **新建前端组件** → 确认放对子目录（components/papers/ 或 components/chat/）
- **完成任务** → 立即更新 `docs/TODO.md`
- **提交代码** → 中文 commit，格式 `类型(范围): 描述`
