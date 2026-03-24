# 开发成长笔记

> 记录 academic-research-agent 从零到完整 demo 过程中遇到的真实问题和解决方案。
> 面向：技术面试准备、个人技术积累、后续 Java 重写参考。

---

## 一、工程架构问题

### 1.1 PDF 处理为什么要用 BackgroundTask？

**问题**：最初想在 `/api/papers/upload` 接口里同步做完"上传 → 解析 → 分块 → Embedding → 入库 Qdrant"全流程，结果 HTTP 请求超时（默认 30s，一篇 PDF 实际需要 1~3 分钟）。

**解决**：

```python
# FastAPI BackgroundTasks 异步处理
@router.post("/upload")
async def upload_paper(file: UploadFile, background_tasks: BackgroundTasks):
    paper = await paper_repo.create(db, ...)   # 先写 DB，status="processing"
    background_tasks.add_task(process_paper, paper.id, file_content)
    return {"id": paper.id, "status": "processing"}   # 立即返回
```

前端轮询 `/api/papers/{id}/status`，直到 `status="ready"` 才允许使用。

**面试考点**：BackgroundTasks vs Celery。BackgroundTasks 运行在同一个 uvicorn 进程内，适合轻量任务；Celery + Redis 适合需要重试、分布式、任务队列的场景。本项目单机部署选 BackgroundTasks 足够。

---

### 1.2 全局状态初始化：AppInitializer 模式

**问题**：论文列表存在 Zustand 全局状态，只有进入"文献库"页面时才会调用 `fetchPapers()`。用户直接访问"问答"或"分析"页时，论文选择器是空的，体验很差。

**解决**：在 Next.js 根 `layout.tsx` 挂载一个纯客户端初始化组件：

```tsx
// components/layout/AppInitializer.tsx
"use client"
export function AppInitializer() {
  const setPapers = useAppStore((s) => s.setPapers)
  useEffect(() => {
    fetchPapers().then(setPapers).catch(() => {})
  }, [setPapers])
  return null   // 不渲染任何 UI
}
```

这是 Next.js App Router 中处理"应用级副作用"的标准模式：Server Component（layout）嵌套 Client Component（AppInitializer）。

---

### 1.3 SSE 流式响应的 CORS 陷阱

**问题**：后端 `StreamingResponse` 正常输出，但前端 `EventSource` 或 `fetch + ReadableStream` 收不到数据，无报错。

**根因**：缺少两个关键 Header：

```python
return StreamingResponse(
    generator(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",       # 禁止代理/浏览器缓存
        "X-Accel-Buffering": "no",         # 禁止 Nginx 缓冲（关键！）
    }
)
```

`X-Accel-Buffering: no` 在有 Nginx 反代时必须设置，否则 Nginx 会等响应结束才转发，SSE 失效。

**面试考点**：SSE vs WebSocket。SSE 是单向（服务器→客户端），基于 HTTP，天然支持断线重连；WebSocket 是双向全双工。LLM 流式输出用 SSE 更合适，前端实现更简单。

---

## 二、数据库问题

### 2.1 SQLAlchemy 204 No Content 导致前端报错

**问题**：删除对话记录时后端返回 204 No Content（无 body），前端公共 `request()` 函数调用 `res.json()` 解析空响应，抛出 `SyntaxError: Unexpected end of JSON input`，前端误认为删除失败。

**解决**：在 API 工具函数里对 204 单独处理：

```ts
async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (res.status === 204) return undefined as T   // 无 body 直接返回
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
```

**教训**：REST 规范中 DELETE 成功返回 204 是标准行为，客户端需要专门处理。

---

### 2.2 SQLAlchemy JSON 列在 PostgreSQL 的正确用法

**问题**：给 `AnalysisORM` 添加 `refinements JSON` 列后，直接 `row.refinements.append(...)` 不生效（SQLAlchemy 无法检测到列表原地修改）。

**解决**：替换整个列表引用，触发"脏检测"：

```python
existing = list(row.refinements or [])   # 复制一份
existing.extend(new_entries)
row.refinements = existing               # 赋新引用，触发 dirty check
await db.commit()
```

**延伸**：如果频繁追加，可以用 `flag_modified(row, "refinements")` 强制标记为已修改，跳过脏检测。

---

### 2.3 新增数据库列的迁移方式

**问题**：AnalysisORM 新增 `refinements` 列后，已有的 PostgreSQL 表没有该列，运行时报 `column "refinements" does not exist`。

**解决（开发阶段快速方案）**：远程 SSH 执行：

```sql
ALTER TABLE analyses ADD COLUMN refinements JSON;
```

**生产方案**：用 Alembic 做数据库迁移，生成迁移脚本并版本管理。本项目 demo 阶段直接 ALTER 足够。

---

## 三、LLM 工程问题

### 3.1 LLM 不遵守 JSON-Only 指令

**问题**：给 Planner 和 Reviewer 设置了 `"Respond with a JSON object ONLY"` 的 system prompt，但代理模型（非官方 GPT）直接返回中文对话、Markdown 报告，完全不输出 JSON。

**根因分析**：

- **Planner**：模型不理解"假设论文已上传"的背景，认为需要向用户索要论文内容
- **Reviewer**：模型把"评审草稿"误理解为"写一篇报告"，生成了完整的分析文章

**三层解决方案（递进）**：

```
方案一：Function Calling 强约束（最终采用）
  llm.with_structured_output(Schema, method="function_calling")
  → 代理层强制 tool_choice，LLM 物理上不能输出 JSON 以外的内容

方案二：parse_json_markdown（降级兜底）
  from langchain_core.utils.json import parse_json_markdown
  → 自动剥除 ```json 围栏，比手写正则更健壮

方案三：带错误反馈的 Retry（最终兜底）
  把原始错误输出反馈给 LLM，要求重新输出 JSON
  → 模拟 OutputFixingParser 行为
```

**面试考点**：

- `with_structured_output(method="function_calling")` 底层是将 Pydantic schema 转换为 OpenAI Tool，然后强制 `tool_choice` 为该工具。LLM 的输出被约束在 tool call arguments 的 JSON 字段内。
- `method="json_schema"` 是更强的约束（服务端 constrained decoding），但只有 GPT-4o 系列支持，代理基本不支持。
- `method="json_mode"` 设置 `response_format: json_object`，保证语法合法但不保证 schema 匹配。

---

### 3.2 RAG 分块粒度与全文模式的权衡

**问题**：使用 RAG（向量检索）做分析时，一篇论文被切成 100-200 个小块（每块约 512 tokens），检索时只返回 top-k（5-20块）。LLM 拿到的信息严重不足，生成的分析报告内容空泛，甚至说"请提供论文内容"。

**根因**：RAG 的分块策略天然适合"问答"场景（精确检索片段），但不适合"深度分析"场景（需要理解全文结构和上下文）。

**解决**：区分两种场景：


| 场景            | 策略             | 原因                |
| ------------- | -------------- | ----------------- |
| 问答（Chat）      | RAG 向量检索 top-k | 用户问题具体，精确定位片段即可   |
| 对比分析（Analyze） | 全文加载（限 60K 字符） | 需要理解两篇论文的完整结构才能对比 |


```python
# 全文模式：轮询交替取块，保证多篇论文均衡覆盖
_MAX_CONTEXT_CHARS = 60_000
for i in range(max_len):
    for paper_chunks in per_paper_chunks:
        if total_chars + len(paper_chunks[i]) > _MAX_CONTEXT_CHARS:
            break
        all_chunks.append(paper_chunks[i])
        total_chars += len(paper_chunks[i])
```

**面试考点**：60K 字符 ≈ 15-20K tokens，这是大多数模型（包括代理）能稳定处理的上限。超出上下文窗口时，LLM 返回空流，LangChain 抛出 `ValueError: No generations found in stream`。

---

### 3.3 LangGraph astream_events 事件解析

**问题**：`research_graph.astream_events()` 返回大量事件，不知道如何区分"节点开始"、"节点输出"、"LLM 流式 token"。

**实际事件类型**（`version="v2"`）：

```python
async for event in graph.astream_events(state, version="v2"):
    kind = event["event"]
    name = event.get("name", "")
    metadata = event.get("metadata", {})

    if kind == "on_chain_start" and name in NODE_LABELS:
        # 节点开始执行
    elif kind == "on_chain_end" and name in NODE_LABELS:
        # 节点执行完毕，event["data"]["output"] 是节点返回值
    elif kind == "on_chat_model_stream" and metadata.get("langgraph_node") == "writer":
        # WriterNode 内 LLM 流式 token
        chunk = event["data"].get("chunk")
        if chunk and chunk.content:
            yield chunk.content
```

关键：用 `metadata["langgraph_node"]` 判断 token 来自哪个节点，避免把 ReviewerNode 的 LLM 输出也流式推送给前端。

---

### 3.4 Context Window 超限导致的静默崩溃

**问题**：加载 330 个文本块（约 10 万字符）后直接全部传给 WriterNode，LLM API 报错 `ValueError: No generations found in stream`，前端收到 500 错误，没有任何提示。

**根因**：LangChain 的 `generate_from_stream(iter(chunks))` 在 stream 为空时抛出该异常，这是 LLM 上下文超限或 API 报错的典型表现。

**解决**：

1. 限制 `_MAX_CONTEXT_CHARS = 60_000`，裁剪输入
2. 多篇论文时轮询交替取块，确保每篇论文都有内容被包含

**教训**：LLM API 的错误信息经常不直观，`No generations found in stream` 实际是"API 调用失败"的包装异常。遇到此类问题先检查实际发送的 token 量。

---

## 四、前端工程问题

### 4.1 IME 中文输入法与 Enter 发送的冲突

**问题**：用户在 Textarea 里用中文输入法选词时，按 Enter 确认候选词会误触发"发送"逻辑。

**根因**：浏览器在 IME 组合输入阶段（从开始输入到选词确认）`isComposing = true`，这期间的 keydown 事件不应触发业务逻辑。

**解决**：

```tsx
const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
  // e.nativeEvent.isComposing === true 表示输入法正在组合字符，不触发发送
  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
    e.preventDefault()
    handleSend()
  }
}
```

**注意**：React 合成事件的 `e.isComposing` 不可靠（总是 false），必须用 `e.nativeEvent.isComposing`。

---

### 4.2 Next.js App Router 中 Server/Client Component 边界

**问题**：在 `layout.tsx`（Server Component）里直接使用 `useEffect`，报 `Error: You're importing a component that needs useState. This only works in a Client Component`。

**解决**：拆分组件，将含 hooks 的逻辑放进独立 `"use client"` 组件：

```
layout.tsx (Server Component)
  └── AppInitializer.tsx (Client Component，"use client"，含 useEffect)
```

**核心原则**：Next.js App Router 默认所有组件是 Server Component；只要用到 hooks（useState/useEffect）或浏览器 API 就必须加 `"use client"`，并且 Client Component 只能被 Server Component 当作"叶子"引入，不能反向包含。

---

### 4.3 Zustand 状态与 React 渲染的时序问题

**问题**：在 `handleAnalyze` 完成后立即从 store 读取 `selectedPaperIds`，有时拿到的是旧值。

**根因**：Zustand 的 `set` 是同步的，但 React 的 re-render 是批量异步的，在同一个事件处理函数中多次 set 后立即读，可能读到 render 前的 snapshot。

**解决**：从 Zustand store 直接用 `getState()` 获取最新值，或者把后续逻辑放到 `set` 的回调里：

```ts
// 获取最新状态（绕过 React render 周期）
const ids = useAppStore.getState().selectedPaperIds
```

---

## 五、第三方 API 兼容问题

### 5.1 qdrant-client 版本与服务端不兼容

**问题**：`qdrant-client 1.17.1` 连接 `qdrant-server 1.13.6` 时报 UserWarning：

```
Major versions should match and minor version difference must not exceed 1
```

同时旧版 `client.search()` API 已被废弃，新版改为 `client.query_points()`。

**解决**：升级 API 调用方式：

```python
# 旧（1.13 以前）
result = client.search(collection_name=name, query_vector=vec, limit=top_k)
# 新（1.14+）
result = client.query_points(collection_name=name, query=vec, limit=top_k)
```

如果升级客户端不可行，可设 `check_compatibility=False` 忽略警告（兼容性风险自担）。

---

### 5.2 第三方 Embedding API 兼容

**问题**：阿里云 DashScope Embedding API 兼容 OpenAI 格式，但有两个坑：

1. `langchain_openai.OpenAIEmbeddings` 默认使用 tiktoken 做 token 计数，但 DashScope 的模型 ID 不在 tiktoken 字典里，报 `KeyError`
2. 默认 batch size（2048）超出 DashScope 限制，报 422 错误

**解决**：

```python
embeddings = OpenAIEmbeddings(
    model=settings.embedding_model,
    openai_api_key=settings.embedding_api_key,
    openai_api_base=settings.embedding_base_url,
    check_embedding_ctx_length=False,   # 禁用 tiktoken 检查
    chunk_size=25,                       # 降低 batch size
)
```

---

### 5.3 日志级别配置：app.* Logger 不输出 INFO

**问题**：`logger = logging.getLogger(__name__)` 后调用 `logger.info(...)` 在控制台看不到输出，只看到 WARNING 以上的日志。

**根因**：Python `logging` 默认 root logger 级别是 WARNING。`app.core.nodes.planner` 这类层级 logger 如果没有显式配置 handler 和 level，会继承 root logger 的 WARNING 级别，INFO 日志被丢弃。

**解决**：在应用入口（`main.py`）配置全局日志：

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

这会设置 root logger 为 INFO，所有子 logger 都会继承。

**进阶**：生产环境建议用 `logging.config.dictConfig()` 对不同模块配置不同级别（如把 `sqlalchemy.engine` 设为 WARNING 避免 SQL 语句刷屏）。

---

## 六、面试高频问题参考

### Q1：你的项目用了 RAG，RAG 的核心原理是什么？

RAG（Retrieval-Augmented Generation）分三步：

1. **离线索引**：文档 → 分块（Chunking）→ Embedding → 存入向量数据库
2. **在线检索**：用户问题 → Embedding → 向量相似度搜索（cosine） → 返回 top-k 相关块
3. **生成**：将检索到的块作为 context 注入 LLM prompt → 生成答案

本项目的向量数据库选用 Qdrant，每篇论文一个 collection，Embedding 模型用阿里云 `text-embedding-v4`（1024 维）。

### Q2：RAG 和直接把文档喂给 LLM 有什么区别？


|       | RAG            | 全文（Long Context）      |
| ----- | -------------- | --------------------- |
| 成本    | 低（只发 top-k 片段） | 高（发全文）                |
| 精度    | 依赖检索质量         | 更好，但受 context 长度限制    |
| 适用场景  | 文档库问答（精确检索）    | 深度分析（需理解全文结构）         |
| 本项目用法 | 问答页（Chat）      | 分析页（Analyze，限 60K 字符） |


### Q3：LangGraph 和 LangChain 的关系？

LangChain 是基础工具库（LLM 调用、Prompt 管理、OutputParser、工具调用等）；LangGraph 是构建在 LangChain 之上的 **Agent 编排框架**，用 StateGraph 表达"有状态的、可循环的"工作流。

本项目中：`PlannerNode → RetrieverNode → WriterNode → ReviewerNode`，ReviewerNode 评分 < 7 时有条件边回到 WriterNode 重写，最多循环 2 次。这种"带条件回路的 DAG"是 LangGraph 的核心能力，普通 LangChain Chain 做不到。

### Q4：你是怎么保证 LLM 输出格式稳定的？

三层防线：

1. **Function Calling**（`with_structured_output(method="function_calling")`）：代理层强制约束，LLM 不能输出 JSON 以外内容。这是最可靠的方案，需要代理支持 OpenAI Tool Calling。
2. **parse_json_markdown**（LangChain 内置）：自动剥除 `\`json` 围栏，比手写正则更健壮。
3. **带错误反馈的 Retry**：把错误输出重新发给 LLM 说"你之前输出有误，请重新输出 JSON"。模拟 `OutputFixingParser` 行为。

### Q5：FastAPI 和 Spring Boot 的对比？


| 维度   | FastAPI                             | Spring Boot       |
| ---- | ----------------------------------- | ----------------- |
| 语言   | Python                              | Java              |
| 性能   | 高（异步 I/O）                           | 高（多线程）            |
| 生态   | AI/ML 工具链无敌（LangChain、Hugging Face） | 企业级生态成熟（安全、事务、监控） |
| 开发效率 | 极高，适合快速原型                           | 较高，约定优于配置         |
| 类型安全 | Pydantic 运行时验证                      | 编译时强类型            |
| 适合场景 | AI 应用、数据管道、微服务                      | 企业系统、金融、电商        |


本项目选 FastAPI 是因为 Python AI 生态完整，后续计划用 Spring AI 做 Java 版本满足 Java 岗位需求。

---

## 五、Agent 框架横向调研（2026-03 更新）

> 调研目的：了解当前主流 Agent 框架的能力边界，为技术选型和面试做准备。
> 信息来源：GitHub WebFetch（jd-opensource/OxyGent、JDOxyGent4J、joyagent-jdgenie）+ 公开文档。

### 5.1 Python Agent 框架总览

| 框架 | 所属 | 编排模型 | Memory | Tool Calling | Multi-Agent | GAIA 得分 | 生产可用性 |
|------|------|---------|--------|-------------|-------------|---------|-----------|
| LangGraph | LangChain AI | StateGraph | Checkpointer（需配PG/Redis） | ✅ ReAct + Function Calling | ✅ | — | ⚠️ 复杂但可用 |
| **OxyGent** | **京东 Oxygen** | ReAct + MAS层级 | ✅ 跨任务工作流记忆 | ✅ MCP + 预设工具 | ✅ 层级主从Agent | **59.14** | ✅ 生产验证 |
| **JoyAgent-JDGenie** | **京东** | Plan+Execute + ReAct | ✅ 跨任务工作流记忆 | ✅ MCP + 工具进化 | ✅ 可插拔子Agent | **75.15% (Val)** | ✅ 完整产品 |
| LlamaIndex | Jerry Liu | QueryEngine | ✅ 简单 | ✅ | ⚠️ 弱 | — | ⚠️ RAG强，Agent弱 |
| CrewAI | CrewAI Inc | Pipeline串/并行 | ❌ | ✅ | ✅ 强 | — | ⚠️ 新兴 |
| AutoGen | Microsoft | Conversation | ❌ | ⚠️ 弱 | ✅ 原生 | — | ⚠️ v2不稳 |

### 5.2 Java Agent 框架总览

| 框架 | 所属 | 编排模型 | Memory | Tool Calling | Multi-Agent | 生产可用性 |
|------|------|---------|--------|-------------|-------------|-----------|
| **JDOxyGent4J** | **京东** | ReAct + MAS | ✅ 可插拔存储层 | ✅ Function Calling | ✅ 层级主从 | ✅ Spring Boot + 生产验证 |
| Spring AI Agent | Spring | Agent + ToolCallback | ✅ 可接 Spring Memory | ✅ Function Calling | ⚠️ 有限 | ⚠️ 早期 |
| LangChain4j | LangChain | StateGraph | ✅ Checkpointer | ✅ ReAct | ⚠️ 发展中 | ⚠️ 活跃但生态追赶中 |
| Semantic Kernel | Microsoft | Planner | ✅ Memory Graph | ✅ Function Calling | ⚠️ | ⚠️ C#为主，Java弱 |

### 5.3 京东三件套详解

#### OxyGent（Python）— GAIA 59.14
- **核心**：多Agent协作框架，"Oxy"组件即插拔单元
- **架构**：MAS（多Agent系统）+ HttpLLM + ReActAgent，支持层级主从Agent拓扑
- **亮点**：内置知识反馈循环（Agent可持续进化）、自动化依赖映射和可视化调试、分布式调度器
- **支持 MCP 协议**：可接入 Model Context Protocol 标准工具生态

#### JDOxyGent4J（Java）— 京东生产验证
- **Spring Boot 深度集成**：注解式定义Agent（`@Agent`）、依赖注入原生支持
- **企业级可靠性**：Java安全模型、异常处理、访问控制、审计日志
- **模块结构**：`oxygent-core`(核心) / `oxygent-infra`(基础设施) / `oxygent-starter-core`(Spring自动配置) / `oxygent-studio`(Web示例UI)
- **存储可插拔**：数据库、缓存、向量库均可配置
- **要求**：Java 17+、Maven 3.6+、Spring Boot 3.2.5+

#### JoyAgent-JDGenie — GAIA 75.15%（超过 OpenManus、CAMEL-OWL 等）
- **定位**：端到端完整产品（不只是框架），输入任务→直接输出 HTML/PPT/报告
- **GAIA 准确率**：Val 集 **75.15%**、Test 集 **65.12%**，是目前开源最高的之一
- **引擎**：高并发 DAG 执行引擎、Plan-and-Execute + ReAct 双模式
- **工具进化**：自动拆解/重组原子工具，生成新能力（超出传统框架的关键特性）
- **子Agent库**：ReportAgent / SearchAgent / CodeAgent / PPTAgent / FileAgent，即插即用
- **部署**：Docker 一键启动，支持 DeepSeek / OpenAI 兼容 API

### 5.4 框架差距总结

```
Python Agent 框架生态完整度：
LangGraph/CrewAI/OxyGent — 生态 70%，Tool Calling 90%，Memory 50%，Multi-Agent 70%
Java Agent 框架：
JDOxyGent4J — 生态 60%，Spring集成强，生产验证好，但生态仍在追赶
Spring AI Agent — 生态 40%，早期，功能在完善
```

### 5.5 对本项目技术路径的影响

**Python 路径**（当前）：LangGraph 是脚手架，你填入的 Memory/Citation/Query Rewrite 是壁垒。
- CrewAI 的角色分工思路值得借鉴（可在 Phase 6 参考）
- JoyAgent 的 GAIA 成绩说明京东的工程化程度很高，值得关注

**Java 路径**（未来重写）：
- **JDOxyGent4J 比 LangChain4j 更值得作为主力框架**：
  - Spring Boot 注解式定义，面试更容易讲清楚
  - 已有京东内部生产验证，不是实验项目
  - 与你现有的 Spring 知识体系无缝衔接
- 选 JDOxyGent4J 作为 Java Agent 面试的核心项目背书，比泛泛说"了解 Spring AI"更有说服力

**真正缺的从来不是框架**：框架解决 60% 的通用问题，40% 的业务壁垒（Memory schema、评测体系、工具适配）才是核心竞争力。