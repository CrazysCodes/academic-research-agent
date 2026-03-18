# 个人职业规划 & 项目方向（2026-03）

## 个人背景

- Java 后端工程师，具备 AI 基础知识
- 研究生期间 CV/目标检测研究，发表 SCI 2区论文
- 两段 Java 后端实习，第二段在 AI 应用平台部
- 正在使用 Claude Code 等 AI 编程工具

---

## 职业方向决策

**目标岗位：AI 应用研发工程师**（优先于全栈研发）

理由：
- CV 论文背景命中 JD 加分项"NLP/CV 理论基础"
- Java 后端 → AI 应用研发路径比 → 前端转型更自然
- AI 应用研发岗本质也是做产品，满足"能看到能用到"的偏好

当前主要缺口：**缺少可展示的 Agent/RAG 完整项目**

---

## 技术栈决策

```
前端：Next.js + TypeScript + Tailwind
后端：FastAPI (Python) + Pydantic
AI层：LangChain / LangGraph
向量库：Qdrant（Docker 启动）
数据库：PostgreSQL
部署：Docker Compose
```

架构分层：
```
Next.js (TypeScript)     ← 前端 + BFF API Routes
      ↕ HTTP
FastAPI (Python)         ← AI 核心逻辑（Agent、RAG、LLM）
      ↕
Qdrant（向量库）+ PostgreSQL
```

各语言定位：
- Python → AI 逻辑层（RAG、Agent、LLM 调用）首选
- Node.js → 配合 Next.js 做 BFF/API 路由，自然选择
- Go → AI 应用层用不上，排除
- Rust → 暂不涉及，排除
- Java → 留着面试，不在新项目里用

---

## FastAPI + Pydantic 后端分层架构

### 框架演进背景
```
Django (2005) → Flask (2010) → FastAPI (2018)
重量级 MVC        轻量微框架      现代异步框架
```
FastAPI 是 AI 应用领域的事实标准，原生支持 async/await，LLM 调用是 IO 密集型，异步是刚需。

### 目录分层结构
```
app/
├── api/              # 路由层（对应 Java Controller）
│   ├── routes/
│   │   ├── papers.py
│   │   └── chat.py
│   └── deps.py       # 依赖注入（认证、DB Session等）
├── services/         # 业务逻辑层（对应 Java Service）
│   ├── rag_service.py
│   └── agent_service.py
├── core/             # 核心 AI 逻辑（Agent、RAG、LLM调用）
│   ├── agents/
│   ├── tools/
│   └── retriever.py
├── models/           # Pydantic 数据模型（对应 Java DTO/VO）
│   ├── request.py
│   └── response.py
├── repositories/     # 数据库操作层（对应 Java Repository/Mapper）
│   └── paper_repo.py
├── config.py         # 配置（env var 读取）
└── main.py           # 入口，挂载路由
```

### Pydantic 的作用
类比 Java 的 Bean Validation + Jackson，但写法更简洁：
```python
# 请求体校验 + 自动生成 OpenAPI 文档
class AnalyzeRequest(BaseModel):
    paper_ids: list[str]
    query: str
    mode: Literal["single", "compare"] = "single"

# 响应体序列化
class AnalyzeResponse(BaseModel):
    answer: str
    sources: list[str]
    tokens_used: int
```

### 性能认知
| 场景 | Python FastAPI | Java Spring |
|---|---|---|
| CPU 密集计算 | 慢 5-10x | 快 |
| IO 密集（网络/DB） | async 下差距很小 | 差不多 |
| LLM API 调用 | 瓶颈在网络和模型，语言不是瓶颈 | 同左 |
| 启动时间 | 快 | JVM 慢 |

**结论**：AI 应用 99% 的瓶颈在 LLM 推理延迟（秒级）和向量检索，Python 的"慢"完全被掩盖。

---

## 项目方向：学术研究 Agent

**定位**：帮助研究者完成从文献调研到辅助写作的全流程

**核心亮点**：
- 复用已有的 2markdown（PDF/Word 解析）作为预处理模块
- CV 论文背景 → 天然是目标用户，需求理解深
- 技术覆盖面对齐 JD 所有关键词

### 功能分层

**必须做（核心链路，2-3周）**
- 多格式文档解析（PDF/Word，复用 2markdown）
- RAG 多文档检索问答
- 多文档对比分析 Agent

**做 Demo 即可（1周）**
- LaTeX 辅助写作（能跑通一个示例）
- Mermaid 图生成（一个 Tool 调用）

**加分项（后续迭代）**
- MCP 集成：暴露 MCP Server，让 Claude Desktop/Cursor 能调用
- A2A 协议：Sub-Agent 拆成独立微服务，标准化跨 Agent 通信

### 技术覆盖

```
文档解析   → 2markdown 复用
RAG        → 多文档检索 + 上下文注入
Agent编排  → LangGraph（多步规划、反思机制）
Tool调用   → Mermaid生成、LaTeX片段、Web搜索
多Agent    → 检索Agent + 写作Agent + 评审Agent（Sub-Agent 思想）
前端       → Next.js 对话界面 + 文档管理
部署       → Docker Compose 一键启动
```

### 部署形式

单应用，不做 LLM 中台/平台。
- 面试价值更高（一句话能说清楚）
- 可以说"内部参考了 AI 中台的分层设计思路"体现认知优势

---

## 关键概念备忘

### Agent 编排 vs A2A 协议

| | Agent 编排（LangGraph）| A2A 协议 |
|---|---|---|
| 范围 | 单进程内多角色协作 | 跨服务独立 Agent 通信 |
| 调用方式 | 函数调用 | HTTP 标准协议 |
| 类比 | 一个应用内多个 Service | 微服务间 RPC |
| 当前阶段 | 主要用这个 | 架构预留，后续做 |

### MCP 集成思路
```python
@mcp_server.tool()
async def search_papers(query: str) -> str:
    # 调用 RAG 检索，暴露给外部 AI 客户端（Claude Desktop/Cursor）
    return results
```

### A2A 集成思路
```
1. 每个 Sub-Agent 暴露 /.well-known/agent.json（Agent Card）
2. 主 Agent 通过 HTTP 发现并调用 Sub-Agent
3. 通信格式遵循 A2A 规范
4. 可用 google-a2a Python SDK
```
