from pydantic import BaseModel
from fastapi import APIRouter

from app.config import settings

router = APIRouter()


def _mask_key(key: str) -> str:
    """脱敏：只显示前4位和后4位"""
    if len(key) <= 8:
        return "****" if key else ""
    return f"{key[:4]}...{key[-4:]}"


class LLMSettings(BaseModel):
    llm_model: str
    openai_api_key: str
    openai_base_url: str
    embedding_model: str
    embedding_api_key: str
    embedding_base_url: str


class LLMSettingsUpdate(BaseModel):
    llm_model: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None


def _current_settings() -> LLMSettings:
    return LLMSettings(
        llm_model=settings.llm_model,
        openai_api_key=_mask_key(settings.openai_api_key),
        openai_base_url=settings.openai_base_url,
        embedding_model=settings.embedding_model,
        embedding_api_key=_mask_key(settings.embedding_api_key),
        embedding_base_url=settings.embedding_base_url,
    )


@router.get("", response_model=LLMSettings)
async def get_settings():
    return _current_settings()


@router.patch("", response_model=LLMSettings)
async def update_settings(req: LLMSettingsUpdate):
    """运行时修改模型配置（不写入 .env，重启恢复默认值）"""
    if req.llm_model is not None:
        settings.llm_model = req.llm_model
    if req.openai_api_key is not None:
        settings.openai_api_key = req.openai_api_key
    if req.openai_base_url is not None:
        settings.openai_base_url = req.openai_base_url
    if req.embedding_model is not None:
        settings.embedding_model = req.embedding_model
    if req.embedding_api_key is not None:
        settings.embedding_api_key = req.embedding_api_key
    if req.embedding_base_url is not None:
        settings.embedding_base_url = req.embedding_base_url
    return _current_settings()
