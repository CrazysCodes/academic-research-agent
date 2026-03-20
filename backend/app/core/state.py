from typing import TypedDict


class ResearchState(TypedDict):
    query: str
    paper_ids: list[str]
    sub_queries: list[str]      # PlannerNode 输出：子查询列表
    context_chunks: list[str]   # RetrieverNode 输出：检索到的文本块
    draft: str                  # WriterNode 输出：草稿报告
    score: int                  # ReviewerNode 输出：质量评分 0-10
    feedback: str               # ReviewerNode 输出：修改意见
    iterations: int             # WriterNode 执行次数（控制反思循环）
