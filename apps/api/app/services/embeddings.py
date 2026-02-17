"""Embedding generation, storage, and semantic search via pgvector.

Uses OpenAI text-embedding-3-small (1536 dims, $0.02/1M tokens).
Provides:
  - generate_embedding(text) -> vector
  - generate_embeddings(texts) -> batch vectors
  - embed_and_store_chunks(resource_id, chunks) -> store in DB
  - search_similar_chunks(query, user_id) -> semantic search
  - backfill_embeddings() -> embed chunks missing embeddings
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.deps import get_admin_client

logger = logging.getLogger("app.services.embeddings")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
BATCH_LIMIT = 2048  # OpenAI max texts per embedding call


def _get_openai_client():
    """Lazy import to avoid import errors in tests without openai."""
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


# ── Single embedding ─────────────────────────────────────────


def generate_embedding(text: str) -> List[float]:
    """Generate a 1536-dim embedding for a single text string."""
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIMS

    client = _get_openai_client()
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text.strip(),
    )
    return resp.data[0].embedding


# ── Batch embeddings ─────────────────────────────────────────


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a batch of texts (max 2048 per call)."""
    if not texts:
        return []

    # Clean inputs — OpenAI rejects empty strings
    cleaned = [t.strip() if t and t.strip() else "empty" for t in texts]

    client = _get_openai_client()
    all_embeddings: List[List[float]] = []

    # Process in batches of BATCH_LIMIT
    for i in range(0, len(cleaned), BATCH_LIMIT):
        batch = cleaned[i:i + BATCH_LIMIT]
        resp = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        # Sort by index to maintain order
        sorted_data = sorted(resp.data, key=lambda x: x.index)
        all_embeddings.extend([d.embedding for d in sorted_data])

    return all_embeddings


# ── Store embeddings for resource chunks ──────────────────────


def embed_and_store_chunks(resource_id: str, chunk_texts: List[str]) -> int:
    """Generate embeddings for chunk texts and update resource_chunks rows.

    Assumes chunks are already inserted into resource_chunks table
    (by _create_chunks in resources router). This function adds the
    embedding column values.

    Returns count of chunks embedded.
    """
    if not chunk_texts:
        return 0

    try:
        embeddings = generate_embeddings(chunk_texts)
    except Exception as e:
        logger.error("Failed to generate embeddings for resource %s: %s", resource_id, e)
        return 0

    admin = get_admin_client()

    # Fetch chunk IDs in order
    chunks_resp = (
        admin.table("resource_chunks")
        .select("id, chunk_index")
        .eq("resource_id", resource_id)
        .order("chunk_index")
        .execute()
    )

    if not chunks_resp.data:
        logger.warning("No chunks found for resource %s", resource_id)
        return 0

    updated = 0
    for chunk_row, embedding in zip(chunks_resp.data, embeddings):
        try:
            admin.table("resource_chunks").update({
                "embedding": embedding,
            }).eq("id", chunk_row["id"]).execute()
            updated += 1
        except Exception as e:
            logger.error("Failed to store embedding for chunk %s: %s", chunk_row["id"], e)

    logger.info(
        "Embedded %d/%d chunks for resource %s",
        updated, len(chunk_texts), resource_id,
    )
    return updated


# ── Semantic search ───────────────────────────────────────────


def search_similar_chunks(
    query: str,
    user_id: str,
    limit: int = 5,
    threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """Search for resource chunks semantically similar to the query.

    Returns list of dicts with: id, resource_id, chunk_index, chunk_text,
    metadata, similarity.
    """
    if not query or not query.strip():
        return []

    try:
        query_embedding = generate_embedding(query)
    except Exception as e:
        logger.error("Failed to generate query embedding: %s", e)
        return []

    admin = get_admin_client()

    try:
        resp = admin.rpc("match_resource_chunks", {
            "query_embedding": query_embedding,
            "match_user_id": user_id,
            "match_count": limit,
            "match_threshold": threshold,
        }).execute()

        return resp.data or []
    except Exception as e:
        logger.error("Vector search failed: %s", e)
        return []


def search_collection_chunks(
    query: str,
    collection_id: str,
    limit: int = 5,
    threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """Search for chunks within a specific collection using semantic similarity.

    Like search_similar_chunks but scoped to one collection instead of user-wide.
    """
    if not query or not query.strip():
        return []

    try:
        query_embedding = generate_embedding(query)
    except Exception as e:
        logger.error("Failed to generate query embedding: %s", e)
        return []

    admin = get_admin_client()

    try:
        resp = admin.rpc("match_collection_chunks", {
            "query_embedding": query_embedding,
            "match_collection_id": collection_id,
            "match_count": limit,
            "match_threshold": threshold,
        }).execute()

        return resp.data or []
    except Exception as e:
        logger.error("Collection vector search failed: %s", e)
        return []


def format_chunks_as_context(chunks: List[Dict[str, Any]]) -> str:
    """Format search results into a text block for LLM context."""
    if not chunks:
        return ""

    parts = []
    for c in chunks:
        title = (c.get("metadata") or {}).get("title", "Resource")
        similarity = c.get("similarity", 0)
        parts.append(
            f"[{title} (relevance: {similarity:.0%})]\n{c['chunk_text']}"
        )

    return "\n\n---\n\n".join(parts)


# ── Backfill ──────────────────────────────────────────────────


def backfill_embeddings(batch_size: int = 100) -> int:
    """Embed all resource_chunks that are missing embeddings.

    Processes in batches to avoid memory issues and API limits.
    Returns total count of chunks embedded.
    """
    admin = get_admin_client()
    total_embedded = 0

    while True:
        # Fetch next batch of unembedded chunks
        resp = (
            admin.table("resource_chunks")
            .select("id, chunk_text")
            .is_("embedding", "null")
            .limit(batch_size)
            .execute()
        )

        if not resp.data:
            break

        texts = [row["chunk_text"] for row in resp.data]
        chunk_ids = [row["id"] for row in resp.data]

        try:
            embeddings = generate_embeddings(texts)
        except Exception as e:
            logger.error("Backfill batch failed: %s", e)
            break

        for chunk_id, embedding in zip(chunk_ids, embeddings):
            try:
                admin.table("resource_chunks").update({
                    "embedding": embedding,
                }).eq("id", chunk_id).execute()
                total_embedded += 1
            except Exception as e:
                logger.error("Failed to backfill chunk %s: %s", chunk_id, e)

        logger.info("Backfill progress: %d chunks embedded so far", total_embedded)

    logger.info("Backfill complete: %d total chunks embedded", total_embedded)
    return total_embedded
