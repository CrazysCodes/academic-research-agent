# Academic Research Agent

> 帮助研究者完成从文献上传 → 多文档检索问答 → 对比分析 → 辅助写作的全流程 AI 助理。

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Next.js 14 · TypeScript · Tailwind CSS · shadcn/ui · Zustand |
| 后端 | FastAPI · Python 3.11 · Pydantic v2 · uv |
| AI | LangChain · LangGraph · OpenAI / Anthropic |
| 向量库 | Qdrant |
| 文档解析 | python-docx (Word) · pymupdf4llm (PDF) |
| 容器化 | Docker · Docker Compose |

## 项目结构

```
academic-research-agent/
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── api/routes/    # 路由层 (papers, chat, analyze)
│   │   ├── services/      # 业务逻辑层
│   │   ├── core/          # AI 核心 (agents, tools, graph)
│   │   ├── models/        # Pydantic 请求/响应模型
│   │   ├── repositories/  # 数据访问层 (Qdrant)
│   │   ├── config.py
│   │   └── main.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/              # Next.js 前端
│   ├── app/               # App Router 页面
│   ├── components/        # UI 组件
│   ├── lib/               # API 封装、Zustand store
│   ├── types/             # 共享类型定义
│   └── Dockerfile
├── docker-compose.yml         # 应用服务 (frontend + backend)
└── docker-compose.infra.yml   # 基础设施 (Qdrant, ...)
```

## 本地开发

### 前置条件

- Python 3.11+ · [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Docker & Docker Compose

### 启动基础设施

```bash
docker compose -f docker-compose.infra.yml up -d
```

### 启动后端

```bash
cd backend
cp .env.example .env   # 填入 API Keys
UV_PROJECT_ENVIRONMENT=../venvs/backend uv sync
UV_PROJECT_ENVIRONMENT=../venvs/backend uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### 启动前端

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
# → http://localhost:3000
```

## Docker 部署

```bash
# 基础设施（首次 / 服务器）
docker compose -f docker-compose.infra.yml up -d

# 应用服务
docker compose up -d --build
```
