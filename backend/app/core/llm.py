"""
LLM factory：统一创建 ChatOpenAI 实例，支持自定义 base_url。

提供两种模式：
- create_chat_llm()         普通模式，流式/非流式皆可
- create_structured_llm()   结构化输出模式，使用 with_structured_output(method="function_calling")
                            要求代理支持 OpenAI Tool Calling 格式
"""
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


def _base_kwargs(streaming: bool = True) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": settings.llm_model,
        "openai_api_key": settings.openai_api_key,
        "streaming": streaming,
    }
    if settings.openai_base_url:
        kwargs["openai_api_base"] = settings.openai_base_url
    return kwargs


def create_chat_llm(streaming: bool = True) -> ChatOpenAI:
    """创建普通 ChatOpenAI 实例。"""
    return ChatOpenAI(**_base_kwargs(streaming))


def create_structured_llm(schema: type[BaseModel], streaming: bool = False):
    """
    创建绑定了结构化输出的 LLM 实例（方案一：Function Calling 模式）。

    使用 with_structured_output(method="function_calling")，
    让代理在 Tool Calling 层面约束输出格式，而非依赖 prompt 指令。

    如果代理不支持 tool_choice 强制，会抛出 API 错误，调用方应捕获并降级。
    返回的 LLM 调用结果直接是 schema 的实例（已由 LangChain 解析和验证）。

    用法示例：
        llm = create_structured_llm(ReviewerOutput)
        result: ReviewerOutput = await llm.ainvoke(messages)
        score = result.score
    """
    llm = ChatOpenAI(**_base_kwargs(streaming))
    return llm.with_structured_output(schema, method="function_calling")
