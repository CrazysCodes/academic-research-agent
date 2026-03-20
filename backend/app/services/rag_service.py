"""
RAG service: chunking → embedding → index / retrieve.
"""
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.repositories import vector_repo

# ---------- 带配置指纹的惰性单例 ----------
# 用创建时的配置值做缓存 key，设置页改了配置后自动重建实例

_embeddings: OpenAIEmbeddings | None = None
_embeddings_fingerprint: tuple = ()

_splitter: RecursiveCharacterTextSplitter | None = None
_splitter_fingerprint: tuple = ()


def _get_embeddings() -> OpenAIEmbeddings:
    global _embeddings, _embeddings_fingerprint
    api_key = settings.embedding_api_key or settings.openai_api_key
    base_url = settings.embedding_base_url or settings.openai_base_url
    fingerprint = (settings.embedding_model, api_key, base_url)

    if _embeddings is None or _embeddings_fingerprint != fingerprint:
        kwargs: dict = {
            "model": settings.embedding_model,
            "openai_api_key": api_key,
        }
        if base_url:
            kwargs["openai_api_base"] = base_url
            # 非官方 OpenAI API 可能不支持 token 数组输入，关闭 tiktoken 预处理
            kwargs["check_embedding_ctx_length"] = False
        kwargs["chunk_size"] = 10  # 第三方 API 单次 batch 上限
        _embeddings = OpenAIEmbeddings(**kwargs)
        _embeddings_fingerprint = fingerprint
    return _embeddings


def _get_splitter() -> RecursiveCharacterTextSplitter:
    global _splitter, _splitter_fingerprint
    fingerprint = (settings.chunk_size, settings.chunk_overlap)

    if _splitter is None or _splitter_fingerprint != fingerprint:
        _splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
        _splitter_fingerprint = fingerprint
    return _splitter


def chunk_text(text: str) -> list[str]:
    return _get_splitter().split_text(text)


async def index_paper(paper_id: str, markdown_text: str) -> int:
    """Chunk → embed → store in Qdrant. Returns chunk count."""
    chunks = chunk_text(markdown_text)
    if not chunks:
        return 0

    embeddings = await _get_embeddings().aembed_documents(chunks)

    vector_repo.create_collection(paper_id)
    vector_repo.upsert_chunks(paper_id, chunks, embeddings)
    return len(chunks)


async def retrieve(paper_ids: list[str], query: str, top_k: int = 5) -> list[str]:
    """Embed query → search Qdrant → return relevant chunks."""
    query_vector = await _get_embeddings().aembed_query(query)
    return vector_repo.search(paper_ids, query_vector, top_k)
