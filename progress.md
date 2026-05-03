# 进度记录

## 2026-05-03

- 创建任务计划文件，开始盘点当前项目现状。
- 盘点到向量库访问集中在 `vector_repo.py` 和 `rag_service.py`，业务 API 对具体向量库耦合较低。
- 通过 Milvus 官方文档确认：Milvus Python 快速上手支持 `MilvusClient`/collection/schema/search；Docker Compose standalone 默认涉及 `milvus-standalone`、`milvus-etcd`、`milvus-minio`，服务端口通常为 19530，WebUI 为 9091。
- 新增 `backend/app/core/nodes/query_rewrite.py`，并将 Query Rewrite 接入 `/api/chat` 与 `/api/analyze`。
- 将 Embedding 维度调整为显式配置项，默认改为 `text-embedding-3-small` + `1536`。
- 更新 TODO：新增 Milvus 可选迁移路线、RAG 评估体系、Agent 评估体系，并将 Query Rewrite 标记为已完成。
- 修正 README、tech-spec、doc-parsing、dev-growth-notes、frontend README 中的技术栈和解析/Embedding 描述。
- 验证通过：后端 `uv run python -m compileall app` 成功；前端 `npm run build` 在授权网络后成功（默认沙箱网络下 Google Fonts 拉取失败）。
- 根据 `~/Desktop/service-init` 更新 `backend/.env`：PostgreSQL 通过 SSH 隧道映射到 `localhost:15432/app`，预留 Milvus `localhost:19530` 和 Redis `localhost:16379`。
- 更新 `frontend/.env.local`：`NEXT_PUBLIC_API_URL=http://localhost:8001`。
- 建立 SSH 隧道并验证端口可达；后端在 `http://127.0.0.1:8001` 启动成功，`/health` 返回 ok，`/api/papers` 返回空列表。
- 服务器 PostgreSQL `app` 库已创建项目表：papers、conversations、messages、analyses 等。
- 前端在 `http://localhost:3000` 启动成功，HTTP 200。
