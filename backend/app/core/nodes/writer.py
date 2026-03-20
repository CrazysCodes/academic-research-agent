"""
WriterNode：根据检索内容生成结构化 Markdown 分析报告。
支持初次写作和基于 ReviewerNode 反馈的修订。
"""
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import create_chat_llm
from app.core.state import ResearchState

_SYSTEM_WRITE = """You are an academic research assistant.
Write a comprehensive, structured analysis report in Markdown.
Use the following sections: ## Summary, ## Key Findings, ## Analysis, ## Conclusion.
Be specific and reference the provided paper excerpts as evidence."""

_SYSTEM_REVISE = """You are an academic research assistant.
The previous draft needs improvement based on reviewer feedback. Revise the report accordingly.
Use the following sections: ## Summary, ## Key Findings, ## Analysis, ## Conclusion.
Address all feedback points specifically."""


async def writer_node(state: ResearchState) -> dict:
    llm = create_chat_llm(streaming=True)
    context = "\n\n---\n\n".join(state["context_chunks"])
    is_revision = state.get("iterations", 0) > 0 and state.get("feedback")

    if is_revision:
        system = _SYSTEM_REVISE
        user_content = (
            f"Research question: {state['query']}\n\n"
            f"Reviewer feedback:\n{state['feedback']}\n\n"
            f"Paper excerpts:\n{context}"
        )
    else:
        system = _SYSTEM_WRITE
        user_content = f"Research question: {state['query']}\n\nPaper excerpts:\n{context}"

    messages = [SystemMessage(content=system), HumanMessage(content=user_content)]
    response = await llm.ainvoke(messages)
    return {
        "draft": response.content,
        "iterations": state.get("iterations", 0) + 1,
    }
