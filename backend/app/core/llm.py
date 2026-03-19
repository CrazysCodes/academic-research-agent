"""
LLM factory: 统一创建 ChatOpenAI 实例，支持自定义 base_url。
"""
from langchain_openai import ChatOpenAI

from app.config import settings


def create_chat_llm(streaming: bool = True) -> ChatOpenAI:
    kwargs: dict = {
        "model": settings.llm_model,
        "openai_api_key": settings.openai_api_key,
        "streaming": streaming,
    }
    if settings.openai_base_url:
        kwargs["openai_api_base"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)
