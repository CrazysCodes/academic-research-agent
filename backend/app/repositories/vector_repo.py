"""
Qdrant vector repository.
One collection per paper: "paper_{paper_id}"
"""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    ScoredPoint,
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
    all_hits: list[ScoredPoint] = []

    for paper_id in paper_ids:
        name = collection_name(paper_id)
        if not client.collection_exists(name):
            continue
        hits = client.search(
            collection_name=name,
            query_vector=query_vector,
            limit=top_k,
        )
        all_hits.extend(hits)

    all_hits.sort(key=lambda h: h.score, reverse=True)
    return [str(h.payload["text"]) for h in all_hits[:top_k]]


def delete_collection(paper_id: str) -> None:
    client = get_client()
    name = collection_name(paper_id)
    if client.collection_exists(name):
        client.delete_collection(name)
