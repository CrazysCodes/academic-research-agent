"""
RAG service: chunking → embedding → index / retrieve.
"""
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import settings
from app.repositories import vector_repo

_embeddings: OpenAIEmbeddings | None = None
_splitter: RecursiveCharacterTextSplitter | None = None


def _get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
        )
    return _embeddings


def _get_splitter() -> RecursiveCharacterTextSplitter:
    global _splitter
    if _splitter is None:
        _splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
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
