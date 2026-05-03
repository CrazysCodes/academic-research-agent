# 当前任务计划

目标：评估 Qdrant 切换 Milvus 的复杂度并更新 TODO；补充 RAG 与 Agent 评估方案；修正文档/配置不一致；实现 Phase 3.0 Query Rewrite。

## 阶段

1. [complete] 盘点当前向量库、RAG、Agent、配置和文档现状
2. [complete] 评估 Qdrant → Milvus 切换复杂度，并写入 TODO
3. [complete] 在 TODO 中补充 RAG 和 Agent 的评估方法、测试集、指标
4. [complete] 修正文档/配置不一致，重点处理 Embedding 维度
5. [complete] 实现 Query Rewrite 并接入 chat/analyze 管线
6. [complete] 运行构建/编译验证，记录结果
7. [complete] 根据 service-init 创建本地启动测试 env，并验证后端/前端启动

## 约束

- 保持现有 Qdrant 主链路可用，Milvus 先做评估与路线图，不贸然切换。
- Query Rewrite 默认应能失败降级，不阻断原有问答和分析。
- 不提交真实 API key，不修改用户未要求的本地环境文件。
- service-init 的服务器内网端口通过 SSH 隧道访问，避免直接暴露公网端口。
