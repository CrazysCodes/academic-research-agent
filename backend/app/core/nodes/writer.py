"""
WriterNode：根据检索内容生成结构化 Markdown 分析报告。
支持两种模式：
  - 初次写作：基于论文全文 + 可选 Web 搜索结果生成报告
  - 修订模式：基于 ReviewerNode 反馈改进上一版报告

Web 搜索：若配置了 TAVILY_API_KEY，初次写作时会对每个子查询执行 Tavily 搜索，
将外部资料作为补充上下文融入报告（仅搜索，不替代论文内容）。
"""
import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import create_chat_llm
from app.core.state import ResearchState
from app.core.tools.web_search import search_web

logger = logging.getLogger(__name__)

_SYSTEM_WRITE = """You are an academic research assistant.
Write a comprehensive, structured analysis report in Markdown.
Use the following sections: ## Summary, ## Key Findings, ## Analysis, ## Conclusion.
Be specific and reference the provided paper excerpts as evidence.
If web search results are provided, use them to supplement the analysis with external context."""

_SYSTEM_REVISE = """You are an academic research assistant.
The previous draft needs improvement based on reviewer feedback. Revise the report accordingly.
Use the following sections: ## Summary, ## Key Findings, ## Analysis, ## Conclusion.
Address all feedback points specifically."""


async def writer_node(state: ResearchState) -> dict:
    """生成或修订分析报告。iterations > 0 且有 feedback 时进入修订模式。"""
    llm = create_chat_llm(streaming=True)
    context = "\n\n---\n\n".join(state["context_chunks"])
    is_revision = state.get("iterations", 0) > 0 and state.get("feedback")
    logger.info(
        "WriterNode 开始，模式=%s，iterations=%d，上下文片段=%d",
        "修订" if is_revision else "初次写作",
        state.get("iterations", 0),
        len(state["context_chunks"]),
    )

    if is_revision:
        system = _SYSTEM_REVISE
        user_content = (
            f"Research question: {state['query']}\n\n"
            f"Reviewer feedback:\n{state['feedback']}\n\n"
            f"Paper excerpts:\n{context}"
        )
    else:
        # 初次写作：并发对所有子查询执行 Web 搜索，补充外部上下文
        sub_queries = state.get("sub_queries") or [state["query"]]
        web_results = await asyncio.gather(*[search_web(q) for q in sub_queries])
        web_context_parts = [r for r in web_results if r]

        if web_context_parts:
            web_section = "\n\n---\n\n".join(web_context_parts)
            logger.info("WriterNode Web 搜索完成，共 %d 条结果", len(web_context_parts))
            user_content = (
                f"Research question: {state['query']}\n\n"
                f"Paper excerpts:\n{context}\n\n"
                f"## Web Search Results (supplementary external context)\n{web_section}"
            )
        else:
            logger.info("WriterNode Web 搜索无结果或未配置 TAVILY_API_KEY，仅使用论文内容")
            user_content = f"Research question: {state['query']}\n\nPaper excerpts:\n{context}"

        system = _SYSTEM_WRITE

    messages = [SystemMessage(content=system), HumanMessage(content=user_content)]
    response = await llm.ainvoke(messages)
    new_iterations = state.get("iterations", 0) + 1
    logger.info("WriterNode 完成，报告长度=%d，iterations=%d", len(response.content), new_iterations)
    return {
        "draft": response.content,
        "iterations": new_iterations,
    }
