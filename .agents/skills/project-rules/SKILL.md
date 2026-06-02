---
name: project-rules
description: academic-research-agent 项目专属开发规范。包含项目结构、技术栈约定、TODO 同步规则、本地联调流程。
---

# academic-research-agent 项目规范

## 项目结构

```
academic-research-agent/          ← monorepo 根
├── backend/                       ← FastAPI 后端
│   ├── app/
│   │   ├── api/routes/            ← 路由层（只做请求/响应）
│   │   ├── services/              ← 业务逻辑层
│   │   ├── core/agents/ tools/    ← LangGraph Agent / Tool
│   │   ├── models/                ← Pydantic 请求/响应模型
│   │   ├── repositories/          ← PostgreSQL / Milvus 数据访问
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
├── docker-compose.infra.yml       ← 基础设施（Milvus / PostgreSQL）
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

### Milvus / Embedding

- 单 collection：`paper_chunks`，通过 `paper_id` 标量过滤区分论文
- Embedding：DashScope `tongyi-embedding-vision-plus-2026-03-06`（1024 维，需显式传 `parameters.dimension`）
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

## 分支规范

本项目按 Phase 或功能模块创建 feature 分支，**不在 main 直接开发**：

```
main                     ← 稳定主干，只合并
feature/phase1-e2e       ← Phase 1 联调
feature/phase2-agents    ← LangGraph Agent
feature/phase3-export    ← 写作辅助导出
fix/xxx                  ← bug 修复
```

**工作流：**
```bash
git checkout -b feature/xxx   # 开始新功能
# 开发 + commit...
git checkout main && git merge feature/xxx
git branch -d feature/xxx
```

---

## 如何使用本规范

- **新增依赖** → 用 `uv add`，不手改 `pyproject.toml`
- **新建后端文件** → 确认放对分层目录（routes / services / core / repositories / models）
- **新建前端组件** → 确认放对子目录（components/papers/ 或 components/chat/）
- **完成任务** → 立即更新 `docs/TODO.md`
- **提交代码** → 中文 commit，格式 `类型(范围): 描述`
- **开发新功能** → 先从 main 切出 feature 分支，完成后再合并
---

## 代码与提交规范

- **Git commit**：提交信息必须使用中文，格式保持 `type(scope): 中文描述`，例如 `feat(frontend): 优化历史记录首屏加载`。
- **必要注释**：代码中遇到复杂业务逻辑、非显然状态流转、兼容性处理、降级策略时，必须补充简洁注释。
- **关键节点注释**：重要流程节点、Agent 节点、异步任务、SSE 流式处理、数据持久化边界等关键环节，需要写清楚“为什么这样做”和“这里承担什么职责”。
- **注释语言**：项目内新增注释统一使用中文，避免中英混杂造成维护成本。
