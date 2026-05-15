"""
RAG service: chunking → embedding → index / retrieve.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol

import httpx
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.repositories import vector_repo

logger = logging.getLogger(__name__)

# ---------- 带配置指纹的惰性单例 ----------
# 用创建时的配置值做缓存 key，设置页改了配置后自动重建实例

class EmbeddingClient(Protocol):
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    async def aembed_query(self, text: str) -> list[float]:
        ...


_embeddings: EmbeddingClient | None = None
_embeddings_fingerprint: tuple = ()

_splitter: RecursiveCharacterTextSplitter | None = None
_splitter_fingerprint: tuple = ()


@dataclass
class DashscopeMultimodalEmbeddings:
    # DashScope 多模态 embedding 接口和 OpenAI embedding 返回格式不同，这里做成兼容适配器。
    model: str
    api_key: str
    endpoint: str
    dimension: int
    chunk_size: int = 10
    timeout: float = 60.0

    async def _embed_contents(self, contents: list[dict]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": {"contents": contents},
            "parameters": {"dimension": self.dimension},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw_embeddings = data.get("output", {}).get("embeddings", [])
        if not raw_embeddings:
            raise ValueError("DashScope embedding response missing output.embeddings")

        raw_embeddings = sorted(raw_embeddings, key=lambda x: int(x.get("index", 0)))
        vectors: list[list[float]] = []
        for item in raw_embeddings:
            vec = item.get("embedding")
            if not isinstance(vec, list) or not vec:
                raise ValueError("DashScope embedding item missing numeric vector")
            vectors.append([float(v) for v in vec])
        return vectors

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        # DashScope 单次请求不宜过大；按小批量发送，避免网关或模型服务拒绝。
        for i in range(0, len(texts), self.chunk_size):
            batch = texts[i : i + self.chunk_size]
            contents = [{"text": text} for text in batch]
            batch_vecs = await self._embed_contents(contents)
            if len(batch_vecs) != len(batch):
                raise ValueError(
                    f"DashScope embedding count mismatch: expected={len(batch)} got={len(batch_vecs)}"
                )
            vectors.extend(batch_vecs)
        return vectors

    async def aembed_query(self, text: str) -> list[float]:
        vecs = await self._embed_contents([{"text": text}])
        return vecs[0]


def _is_dashscope_multimodal(base_url: str, model: str) -> bool:
    return "dashscope.aliyuncs.com" in base_url or model.startswith("tongyi-embedding-vision")


def _get_embeddings() -> EmbeddingClient:
    global _embeddings, _embeddings_fingerprint
    api_key = settings.embedding_api_key or settings.openai_api_key
    base_url = settings.embedding_base_url or settings.openai_base_url
    fingerprint = (
        settings.embedding_model,
        settings.embedding_dim,
        api_key,
        base_url,
        settings.dashscope_embedding_url,
    )

    if _embeddings is None or _embeddings_fingerprint != fingerprint:
        if _is_dashscope_multimodal(base_url, settings.embedding_model):
            # tongyi-embedding-vision* 走 DashScope 原生多模态 endpoint，不经过 OpenAIEmbeddings。
            if not api_key:
                raise ValueError("DASHSCOPE_API_KEY is required for DashScope multimodal embedding")
            _embeddings = DashscopeMultimodalEmbeddings(
                model=settings.embedding_model,
                api_key=api_key,
                endpoint=settings.dashscope_embedding_url,
                dimension=settings.embedding_dim,
                chunk_size=10,
            )
        else:
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


def _preview(text: str, limit: int = 120) -> str:
    return " ".join(text.split())[:limit]


async def index_paper(paper_id: str, markdown_text: str) -> int:
    """Chunk → embed → store in Milvus. Returns chunk count."""
    # 摄入链路：解析后的 Markdown 先分块，再向量化，最后按 paper_id 写入共享 Milvus collection。
    chunks = chunk_text(markdown_text)
    if not chunks:
        return 0

    embeddings = await _get_embeddings().aembed_documents(chunks)

    vector_repo.upsert_chunks(paper_id, chunks, embeddings)
    return len(chunks)


async def retrieve(paper_ids: list[str], query: str, top_k: int = 5) -> list[str]:
    """Embed query → search Milvus → return relevant chunks."""
    logger.info("RAG retrieve: query=%r papers=%s top_k=%d", query, paper_ids, top_k)
    query_vector = await _get_embeddings().aembed_query(query)
    chunks = vector_repo.search(paper_ids, query_vector, top_k)
    logger.info("RAG retrieve done: query=%r chunks=%d", query, len(chunks))
    return chunks


async def retrieve_multi(paper_ids: list[str], queries: list[str], top_k: int = 5) -> list[str]:
    """Retrieve with multiple query variants and round-robin chunks by query."""
    logger.info("RAG retrieve_multi: papers=%s top_k=%d queries=%s", paper_ids, top_k, queries)
    per_query_results: list[tuple[str, list[str]]] = []
    per_query_top_k = max(top_k, 5)
    for query in queries:
        chunks = await retrieve(paper_ids, query, top_k=per_query_top_k)
        per_query_results.append((query, chunks))
        logger.info(
            "RAG retrieve_multi query result: query=%r chunks=%d previews=%s",
            query,
            len(chunks),
            [_preview(chunk) for chunk in chunks[:3]],
        )

    seen: set[str] = set()
    chunks: list[str] = []
    max_len = max((len(result) for _, result in per_query_results), default=0)
    # 多路 query 的结果按轮询合并，避免某一个 query 的相似结果挤掉其他检索意图。
    for rank in range(max_len):
        for query, result in per_query_results:
            if rank >= len(result):
                continue
            chunk = result[rank]
            if chunk in seen:
                continue
            seen.add(chunk)
            chunks.append(chunk)
            logger.info(
                "RAG retrieve_multi selected: source_query=%r rank=%d preview=%r",
                query,
                rank + 1,
                _preview(chunk),
            )
            if len(chunks) >= top_k:
                logger.info("RAG retrieve_multi done: selected=%d", len(chunks))
                return chunks
    logger.info("RAG retrieve_multi done: selected=%d", len(chunks))
    return chunks[:top_k]
