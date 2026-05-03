# 发现记录

## 初始观察

- 当前向量库实现集中在 `backend/app/repositories/vector_repo.py`，采用 Qdrant “每篇论文一个 collection”的模型。
- 当前 RAG 检索在 `backend/app/services/rag_service.py`，仅做 query embedding → Qdrant 纯向量检索。
- 当前分析管线在 `backend/app/api/routes/analyze.py`，会在进入 LangGraph 前预加载论文全文块，限制约 60K 字符。
- README/TODO 中仍有 Next.js 14 等表述，但实际前端依赖为 Next.js 16.1.7 / React 19.2.3。
- `config.py` 默认 `embedding_model=text-embedding-3-small`，但 `embedding_dim=1024`，存在维度不匹配风险。

## 待确认风险

- 如果用户实际使用 `text-embedding-v4` 或第三方 embedding 模型，Qdrant collection 维度必须与返回向量一致。
- Milvus 切换不只是替换 SDK，还涉及 collection/schema、过滤策略、部署依赖和迁移脚本。

## Milvus 切换评估

- 代码复杂度：中等偏低。当前仓储接口集中，主要新增/替换向量仓储实现，`rag_service` 可以维持同样的 `create_collection/upsert/search/get_all_chunks/delete_collection` 语义。
- 部署复杂度：中等。Milvus standalone Docker Compose 通常需要 Milvus + etcd + MinIO，资源占用和运维组件多于当前 Qdrant 单容器。
- 数据迁移复杂度：中等。现有 Qdrant payload 只有 `text/chunk_index`，迁移模型简单；但每篇论文一个 collection 的设计迁移到 Milvus 时需要选择“继续 collection per paper”或“单 collection + paper_id 标量过滤”。
- 建议：可以接受，但不建议立即主线切换；更适合 TODO 中作为可选 Phase，先抽象 VectorStore 接口，再做 Milvus Adapter 和迁移脚本。
