"""
Milvus vector repository.

The app stores all paper chunks in one collection and uses `paper_id` as a
scalar filter. This fits Milvus better than creating one collection per paper,
while preserving the old repository functions used by the rest of the app.
"""
import json
import logging

from pymilvus import DataType, MilvusClient

from app.config import settings

logger = logging.getLogger(__name__)

_client: MilvusClient | None = None


def get_client() -> MilvusClient:
    global _client
    if _client is None:
        kwargs = {"uri": settings.milvus_uri}
        if settings.milvus_token:
            kwargs["token"] = settings.milvus_token
        _client = MilvusClient(**kwargs)
    return _client


def collection_name(_paper_id: str | None = None) -> str:
    return settings.milvus_collection


def _quote(value: str) -> str:
    return json.dumps(value)


def _paper_filter(paper_id: str) -> str:
    return f"paper_id == {_quote(paper_id)}"


def _preview(text: str, limit: int = 120) -> str:
    return " ".join(text.split())[:limit]


def _collection_vector_dim(client: MilvusClient, name: str) -> int | None:
    desc = client.describe_collection(name)
    for field in desc.get("fields", []):
        if field.get("name") == "vector":
            params = field.get("params") or {}
            dim = params.get("dim")
            return int(dim) if dim is not None else None
    return None


def create_collection(_paper_id: str | None = None, vector_dim: int | None = None) -> None:
    """Ensure the shared Milvus collection exists."""
    client = get_client()
    name = collection_name()
    dim = vector_dim or settings.embedding_dim
    if client.has_collection(name):
        existing_dim = _collection_vector_dim(client, name)
        if existing_dim is not None and existing_dim != dim:
            raise ValueError(
                f"Milvus collection {name!r} vector dim is {existing_dim}, "
                f"but current embedding dim is {dim}. Drop/recreate the collection "
                "after changing EMBEDDING_MODEL or EMBEDDING_DIM."
            )
        return

    schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=False,
    )
    schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
    schema.add_field("paper_id", DataType.VARCHAR, max_length=64)
    schema.add_field("chunk_index", DataType.INT64)
    schema.add_field("text", DataType.VARCHAR, max_length=65535)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dim)

    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type=settings.milvus_index_type,
        metric_type="COSINE",
    )

    client.create_collection(
        collection_name=name,
        schema=schema,
        index_params=index_params,
    )
    logger.info("Milvus collection created: %s (dim=%d)", name, dim)


def upsert_chunks(paper_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    client = get_client()
    name = collection_name()

    if len(chunks) != len(embeddings):
        raise ValueError(f"chunks/embeddings length mismatch: {len(chunks)} != {len(embeddings)}")
    if not embeddings or not embeddings[0]:
        raise ValueError("empty embedding vector")

    vector_dim = len(embeddings[0])
    create_collection(paper_id, vector_dim=vector_dim)

    if settings.embedding_dim != vector_dim:
        logger.warning(
            "Embedding dim mismatch with configured EMBEDDING_DIM: actual=%d configured=%d",
            vector_dim,
            settings.embedding_dim,
        )

    # Re-indexing the same paper should replace its old chunks.
    delete_collection(paper_id)

    rows = [
        {
            "id": f"{paper_id}_{i}",
            "paper_id": paper_id,
            "chunk_index": i,
            "text": chunk,
            "vector": embedding,
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    if rows:
        client.insert(collection_name=name, data=rows)
        client.flush(collection_name=name)


def search(
    paper_ids: list[str],
    query_vector: list[float],
    top_k: int = 5,
) -> list[str]:
    """Search selected papers in the shared Milvus collection."""
    client = get_client()
    name = collection_name()
    if not client.has_collection(name):
        return []

    quoted_ids = ", ".join(_quote(pid) for pid in paper_ids)
    expr = f"paper_id in [{quoted_ids}]"
    result = client.search(
        collection_name=name,
        data=[query_vector],
        anns_field="vector",
        filter=expr,
        limit=top_k,
        output_fields=["text", "paper_id", "chunk_index"],
    )

    hits = result[0] if result else []
    logger.info(
        "Milvus search: papers=%s top_k=%d hits=%d",
        paper_ids,
        top_k,
        len(hits),
    )
    for rank, hit in enumerate(hits, start=1):
        entity = hit.get("entity", {})
        logger.info(
            "Milvus hit #%d: score=%s paper_id=%s chunk_index=%s text=%r",
            rank,
            hit.get("distance") or hit.get("score"),
            entity.get("paper_id"),
            entity.get("chunk_index"),
            _preview(str(entity.get("text", ""))),
        )
    return [str(hit["entity"]["text"]) for hit in hits]


def get_all_chunks(paper_id: str) -> list[dict]:
    """Return all chunks for a paper ordered by chunk_index."""
    client = get_client()
    name = collection_name()
    if not client.has_collection(name):
        return []

    rows = client.query(
        collection_name=name,
        filter=_paper_filter(paper_id),
        output_fields=["chunk_index", "text"],
        limit=10000,
    )
    return sorted(
        [{"index": int(row["chunk_index"]), "text": str(row["text"])} for row in rows],
        key=lambda x: x["index"],
    )


def delete_collection(paper_id: str) -> None:
    """Delete all vector chunks for one paper."""
    client = get_client()
    name = collection_name()
    if not client.has_collection(name):
        return
    client.delete(collection_name=name, filter=_paper_filter(paper_id))
    client.flush(collection_name=name)
