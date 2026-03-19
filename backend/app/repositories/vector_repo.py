"""
Qdrant vector repository.
One collection per paper: "paper_{paper_id}"
"""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
from app.config import settings

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return _client


def collection_name(paper_id: str) -> str:
    return f"paper_{paper_id}"


def create_collection(paper_id: str) -> None:
    client = get_client()
    name = collection_name(paper_id)
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_dim,
                distance=Distance.COSINE,
            ),
        )


def upsert_chunks(paper_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    client = get_client()
    points = [
        PointStruct(
            id=i,
            vector=embedding,
            payload={"text": chunk, "chunk_index": i},
        )
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    client.upsert(collection_name=collection_name(paper_id), points=points)


def search(
    paper_ids: list[str],
    query_vector: list[float],
    top_k: int = 5,
) -> list[str]:
    """Search across multiple paper collections, return top-k text chunks."""
    client = get_client()
    all_hits = []

    for paper_id in paper_ids:
        name = collection_name(paper_id)
        if not client.collection_exists(name):
            continue
        result = client.query_points(
            collection_name=name,
            query=query_vector,
            limit=top_k,
        )
        all_hits.extend(result.points)

    all_hits.sort(key=lambda h: h.score, reverse=True)
    return [str(h.payload["text"]) for h in all_hits[:top_k]]


def get_all_chunks(paper_id: str) -> list[dict]:
    """返回该论文所有切块，按 chunk_index 排序。"""
    client = get_client()
    name = collection_name(paper_id)
    if not client.collection_exists(name):
        return []
    points, _ = client.scroll(collection_name=name, limit=10000)
    return sorted(
        [{"index": p.payload["chunk_index"], "text": p.payload["text"]} for p in points],
        key=lambda x: x["index"],
    )


def delete_collection(paper_id: str) -> None:
    client = get_client()
    name = collection_name(paper_id)
    if client.collection_exists(name):
        client.delete_collection(name)
