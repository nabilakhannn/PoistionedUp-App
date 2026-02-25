"""Collection endpoints: CRUD, Voice DNA analysis, scoped search."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.collection import (
    CollectionAddResources,
    CollectionCreate,
    CollectionDetail,
    CollectionResourceOut,
    CollectionSearchRequest,
    CollectionSearchResponse,
    CollectionSearchResult,
    CollectionSummary,
    CollectionUpdate,
    VoiceDNA,
    VoiceDNAResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["collections"])


# ── Helpers ──────────────────────────────────────────────


def _get_collection_or_404(admin, collection_id: str, user_id: str):
    """Fetch a collection row, 404 if not found or not owned."""
    resp = (
        admin.table("collections")
        .select("*")
        .eq("id", collection_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    return resp.data[0]


def _get_resource_count(admin, collection_id: str) -> int:
    """Count resources in a collection."""
    resp = (
        admin.table("resources")
        .select("id", count="exact")
        .eq("collection_id", collection_id)
        .execute()
    )
    return len(resp.data) if resp.data else 0


def _get_collection_resources(admin, collection_id: str) -> List[CollectionResourceOut]:
    """Fetch resources belonging to a collection with chunk counts and content preview."""
    resp = (
        admin.table("resources")
        .select("id, type, title, source_url, content_text, created_at")
        .eq("collection_id", collection_id)
        .order("created_at", desc=True)
        .execute()
    )
    if not resp.data:
        return []

    # Get chunk counts
    resource_ids = [r["id"] for r in resp.data]
    chunk_counts = {}
    if resource_ids:
        chunks_resp = (
            admin.table("resource_chunks")
            .select("resource_id")
            .in_("resource_id", resource_ids)
            .execute()
        )
        for row in chunks_resp.data:
            rid = row["resource_id"]
            chunk_counts[rid] = chunk_counts.get(rid, 0) + 1

    results = []
    for r in resp.data:
        content = r.get("content_text") or ""
        # Check if transcript has been extracted (content has [TRANSCRIPT] marker + text after it)
        has_transcript = "[TRANSCRIPT]" in content and len(content.split("[TRANSCRIPT]", 1)[-1].strip()) > 50
        # Build preview: take first 500 chars after the [TRANSCRIPT] marker if present
        if has_transcript:
            transcript_text = content.split("[TRANSCRIPT]", 1)[-1].strip()
            preview = transcript_text[:500]
        else:
            preview = content[:500] if content else ""

        results.append(
            CollectionResourceOut(
                id=r["id"],
                type=r["type"],
                title=r["title"],
                source_url=r.get("source_url"),
                chunk_count=chunk_counts.get(r["id"], 0),
                content_preview=preview,
                has_transcript=has_transcript,
                created_at=r["created_at"],
            )
        )

    return results


# ── CRUD ─────────────────────────────────────────────────


@router.post("", response_model=CollectionSummary, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new collection (knowledge folder)."""
    admin = get_admin_client()

    insert_data = {
        "user_id": user.id,
        "name": body.name,
        "description": body.description,
        "creator_url": body.creator_url,
    }
    if body.brand_id:
        insert_data["brand_id"] = body.brand_id

    resp = (
        admin.table("collections")
        .insert(insert_data)
        .execute()
    )

    row = resp.data[0]
    return CollectionSummary(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        creator_url=row.get("creator_url"),
        resource_count=0,
        voice_dna_ready=False,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=List[CollectionSummary])
async def list_collections(
    brand_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """List all collections for the authenticated user, optionally filtered by brand."""
    admin = get_admin_client()

    query = (
        admin.table("collections")
        .select("*")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()

    if not resp.data:
        return []

    # Get resource counts per collection
    collection_ids = [r["id"] for r in resp.data]
    count_map = {}
    if collection_ids:
        res_resp = (
            admin.table("resources")
            .select("collection_id")
            .in_("collection_id", collection_ids)
            .execute()
        )
        for row in res_resp.data:
            cid = row["collection_id"]
            count_map[cid] = count_map.get(cid, 0) + 1

    return [
        CollectionSummary(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            creator_url=r.get("creator_url"),
            resource_count=count_map.get(r["id"], 0),
            voice_dna_ready=bool(r.get("voice_dna", {}).get("tone")),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in resp.data
    ]


@router.get("/{collection_id}", response_model=CollectionDetail)
async def get_collection(
    collection_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a collection with its resources and Voice DNA."""
    admin = get_admin_client()
    row = _get_collection_or_404(admin, collection_id, user.id)
    resources = _get_collection_resources(admin, collection_id)

    voice_dna_data = row.get("voice_dna", {}) or {}

    return CollectionDetail(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        creator_url=row.get("creator_url"),
        voice_dna=VoiceDNA(**voice_dna_data) if voice_dna_data.get("tone") else VoiceDNA(),
        resources=resources,
        metadata=row.get("metadata", {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/{collection_id}", response_model=CollectionSummary)
async def update_collection(
    collection_id: str,
    body: CollectionUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update collection name, description, or creator URL."""
    admin = get_admin_client()
    _get_collection_or_404(admin, collection_id, user.id)

    update_data = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.description is not None:
        update_data["description"] = body.description
    if body.creator_url is not None:
        update_data["creator_url"] = body.creator_url

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    resp = (
        admin.table("collections")
        .update(update_data)
        .eq("id", collection_id)
        .eq("user_id", user.id)
        .execute()
    )

    row = resp.data[0]
    return CollectionSummary(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        creator_url=row.get("creator_url"),
        resource_count=_get_resource_count(admin, collection_id),
        voice_dna_ready=bool(row.get("voice_dna", {}).get("tone")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a collection. Resources keep existing (collection_id set to NULL)."""
    admin = get_admin_client()
    _get_collection_or_404(admin, collection_id, user.id)

    # Resources stay — FK ON DELETE SET NULL handles this
    admin.table("collections").delete().eq("id", collection_id).eq("user_id", user.id).execute()


# ── Resource assignment ─────────────────────────────────


@router.post("/{collection_id}/resources", status_code=status.HTTP_200_OK)
async def add_resources_to_collection(
    collection_id: str,
    body: CollectionAddResources,
    user: CurrentUser = Depends(get_current_user),
):
    """Add existing resources to a collection."""
    admin = get_admin_client()
    _get_collection_or_404(admin, collection_id, user.id)

    # Verify all resources belong to this user
    res_resp = (
        admin.table("resources")
        .select("id")
        .eq("user_id", user.id)
        .in_("id", body.resource_ids)
        .execute()
    )
    found_ids = {r["id"] for r in res_resp.data}
    missing = set(body.resource_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resources not found: {', '.join(missing)}",
        )

    # Update collection_id for each resource
    updated = 0
    for rid in body.resource_ids:
        admin.table("resources").update({
            "collection_id": collection_id,
        }).eq("id", rid).eq("user_id", user.id).execute()
        updated += 1

    return {"message": f"{updated} resources added to collection", "updated": updated}


@router.delete("/{collection_id}/resources/{resource_id}", status_code=status.HTTP_200_OK)
async def remove_resource_from_collection(
    collection_id: str,
    resource_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Remove a resource from a collection (resource keeps existing)."""
    admin = get_admin_client()
    _get_collection_or_404(admin, collection_id, user.id)

    # Verify resource exists and belongs to this collection
    res_resp = (
        admin.table("resources")
        .select("id")
        .eq("id", resource_id)
        .eq("user_id", user.id)
        .eq("collection_id", collection_id)
        .execute()
    )
    if not res_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found in this collection",
        )

    admin.table("resources").update({
        "collection_id": None,
    }).eq("id", resource_id).eq("user_id", user.id).execute()

    return {"message": "Resource removed from collection"}


# ── Voice DNA analysis ──────────────────────────────────


@router.post("/{collection_id}/analyze-voice", response_model=VoiceDNAResponse)
async def analyze_voice(
    collection_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Extract Voice DNA from a collection's content.

    Analyzes all resource chunks in the collection to build a structured
    writing style profile. Requires at least 5 chunks (about 2-3 resources).
    """
    admin = get_admin_client()
    row = _get_collection_or_404(admin, collection_id, user.id)

    try:
        from app.services.voice_analysis import analyze_voice_dna
        voice_dna = analyze_voice_dna(admin, collection_id, row["name"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Voice DNA analysis failed for collection %s: %s", collection_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Voice analysis failed. Please try again.",
        )

    return VoiceDNAResponse(
        collection_id=collection_id,
        collection_name=row["name"],
        voice_dna=VoiceDNA(**voice_dna),
        message=f"Voice DNA extracted from {voice_dna.get('analysis_chunk_count', 0)} content samples.",
    )


# ── Collection-scoped search ────────────────────────────


@router.post("/{collection_id}/search", response_model=CollectionSearchResponse)
async def search_collection(
    collection_id: str,
    body: CollectionSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Semantic search within a specific collection."""
    admin = get_admin_client()
    row = _get_collection_or_404(admin, collection_id, user.id)

    try:
        from app.services.embeddings import search_collection_chunks, format_chunks_as_context
        chunks = search_collection_chunks(
            body.query, collection_id,
            limit=body.limit, threshold=body.threshold,
        )
    except Exception as e:
        logger.error("Collection search failed: %s", e)
        chunks = []

    # Enrich results with resource titles
    results = []
    resource_titles = {}
    if chunks:
        resource_ids = list({c["resource_id"] for c in chunks})
        title_resp = (
            admin.table("resources")
            .select("id, title")
            .in_("id", resource_ids)
            .execute()
        )
        resource_titles = {r["id"]: r["title"] for r in title_resp.data}

    for c in chunks:
        results.append(CollectionSearchResult(
            chunk_text=c["chunk_text"],
            resource_title=resource_titles.get(c["resource_id"], "Unknown"),
            similarity=c["similarity"],
            metadata=c.get("metadata", {}),
        ))

    return CollectionSearchResponse(
        collection_id=collection_id,
        collection_name=row["name"],
        query=body.query,
        results=results,
    )
