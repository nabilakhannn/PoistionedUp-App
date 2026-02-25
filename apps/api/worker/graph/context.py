"""Shared context-fetching utilities for pipeline nodes.

Centralises resource retrieval so every node uses the same logic
instead of duplicating _fetch_relevant_resources.
"""

import logging

logger = logging.getLogger("app.worker.graph.context")


def fetch_relevant_resources(query: str, user_id: str, limit: int = 5) -> str:
    """Fetch relevant resource chunks via semantic search. Graceful fallback."""
    if not user_id:
        return "No user context available for resource search."
    try:
        from app.services.embeddings import search_similar_chunks, format_chunks_as_context
        chunks = search_similar_chunks(query, user_id, limit=limit)
        context = format_chunks_as_context(chunks)
        return context if context else "No relevant resources found."
    except Exception as e:
        logger.debug("Resource retrieval unavailable: %s", e)
        return "No relevant resources found."
