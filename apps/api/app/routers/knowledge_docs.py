"""Knowledge Documents Router — Slice 90.

Two-tier knowledge base for agents:
  scope='system' — app owner sets platform SOPs; all users inherit automatically
  scope='user'   — per-brand docs that layer on top of system SOPs

Endpoints (all JWT-protected):
  GET    /knowledge-docs          — list docs (system + user's own)
  POST   /knowledge-docs          — create a user doc
  PATCH  /knowledge-docs/{id}     — update a user doc
  DELETE /knowledge-docs/{id}     — delete a user doc

Agent access (pipeline-key):
  GET    /orchestrator/knowledge-docs  — all relevant docs for an agent run
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.deps import get_admin_client
import hmac

logger = logging.getLogger("app.routers.knowledge_docs")

router = APIRouter(tags=["knowledge-docs"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_DOC_TYPES = {"writing_sop", "cold_email", "framework", "ad_copy", "case_study", "other"}
VALID_PLATFORMS = {"linkedin", "youtube", "twitter", "email", "all"}


# ── Auth ───────────────────────────────────────────────────────────────────


def _require_pipeline_key(
    x_pipeline_key: str = Header(..., alias="X-Pipeline-Key"),
) -> None:
    if not settings.pipeline_secret_key:
        raise HTTPException(503, "Pipeline key not configured.")
    if not hmac.compare_digest(x_pipeline_key, settings.pipeline_secret_key):
        raise HTTPException(401, "Invalid pipeline key")


# ── Schemas ────────────────────────────────────────────────────────────────


class KnowledgeDocResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    brand_id: Optional[str] = None
    title: str
    content: str
    doc_type: str
    platform: str
    scope: str
    agent_scope: List[str]
    created_at: str
    updated_at: str


class CreateDocRequest(BaseModel):
    brand_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    doc_type: str = Field(default="other")
    platform: str = Field(default="all")
    agent_scope: List[str] = Field(default_factory=list)


class UpdateDocRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1)
    doc_type: Optional[str] = None
    platform: Optional[str] = None
    agent_scope: Optional[List[str]] = None


def _row_to_response(row: dict) -> KnowledgeDocResponse:
    return KnowledgeDocResponse(
        id=row["id"],
        user_id=row.get("user_id"),
        brand_id=row.get("brand_id"),
        title=row["title"],
        content=row["content"],
        doc_type=row.get("doc_type", "other"),
        platform=row.get("platform", "all"),
        scope=row.get("scope", "user"),
        agent_scope=row.get("agent_scope") or [],
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/knowledge-docs", response_model=List[KnowledgeDocResponse])
async def list_knowledge_docs(
    brand_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    platform: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """List system docs + user's own docs for a brand."""
    if brand_id and not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    sb = get_admin_client()

    # System docs (everyone sees these)
    sys_q = sb.table("knowledge_documents").select("*").eq("scope", "system")
    if doc_type:
        sys_q = sys_q.eq("doc_type", doc_type)
    if platform and platform != "all":
        sys_q = sys_q.in_("platform", [platform, "all"])
    system_docs = sys_q.execute().data or []

    # User docs
    user_q = (
        sb.table("knowledge_documents")
        .select("*")
        .eq("scope", "user")
        .eq("user_id", user.id)
    )
    if brand_id:
        user_q = user_q.eq("brand_id", brand_id)
    if doc_type:
        user_q = user_q.eq("doc_type", doc_type)
    if platform and platform != "all":
        user_q = user_q.in_("platform", [platform, "all"])
    user_docs = user_q.order("created_at", desc=True).execute().data or []

    return [_row_to_response(row) for row in system_docs + user_docs]


@router.post("/knowledge-docs", response_model=KnowledgeDocResponse, status_code=201)
async def create_knowledge_doc(
    body: CreateDocRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a user-scoped knowledge document."""
    if body.brand_id and not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    # Validate doc_type and platform
    doc_type = body.doc_type if body.doc_type in VALID_DOC_TYPES else "other"
    platform = body.platform if body.platform in VALID_PLATFORMS else "all"

    sb = get_admin_client()
    row = {
        "user_id": user.id,
        "brand_id": body.brand_id,
        "title": body.title[:255],
        "content": body.content,
        "doc_type": doc_type,
        "platform": platform,
        "scope": "user",
        "agent_scope": body.agent_scope,
    }

    result = sb.table("knowledge_documents").insert(row).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create document")

    return _row_to_response(result.data[0])


@router.patch("/knowledge-docs/{doc_id}", response_model=KnowledgeDocResponse)
async def update_knowledge_doc(
    doc_id: str,
    body: UpdateDocRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Update a user-scoped knowledge document."""
    if not _UUID_RE.match(doc_id):
        raise HTTPException(400, "Invalid doc_id")

    updates = {}
    if body.title is not None:
        updates["title"] = body.title[:255]
    if body.content is not None:
        updates["content"] = body.content
    if body.doc_type is not None:
        updates["doc_type"] = body.doc_type if body.doc_type in VALID_DOC_TYPES else "other"
    if body.platform is not None:
        updates["platform"] = body.platform if body.platform in VALID_PLATFORMS else "all"
    if body.agent_scope is not None:
        updates["agent_scope"] = body.agent_scope

    if not updates:
        raise HTTPException(400, "No fields to update")

    updates["updated_at"] = "now()"

    sb = get_admin_client()
    result = (
        sb.table("knowledge_documents")
        .update(updates)
        .eq("id", doc_id)
        .eq("user_id", user.id)
        .eq("scope", "user")  # Users cannot edit system docs
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Document not found or not editable")

    return _row_to_response(result.data[0])


@router.delete("/knowledge-docs/{doc_id}", status_code=204)
async def delete_knowledge_doc(
    doc_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a user-scoped knowledge document."""
    if not _UUID_RE.match(doc_id):
        raise HTTPException(400, "Invalid doc_id")

    sb = get_admin_client()
    result = (
        sb.table("knowledge_documents")
        .delete()
        .eq("id", doc_id)
        .eq("user_id", user.id)
        .eq("scope", "user")
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Document not found or not deletable")

    return None


# ── Agent endpoint (pipeline-key auth) ────────────────────────────────────


@router.get("/orchestrator/knowledge-docs")
async def get_knowledge_docs_for_agent(
    user_id: str,
    brand_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    platform: Optional[str] = None,
    _key: None = Depends(_require_pipeline_key),
):
    """Return all relevant knowledge docs for an agent run.

    Called by jumbo_pipeline.get_knowledge_docs() during pipeline execution.
    Returns system SOPs + user docs, filtered by agent scope if specified.
    """
    if not _UUID_RE.match(user_id):
        raise HTTPException(400, "Invalid user_id")
    if brand_id and not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    try:
        sb = get_admin_client()

        # System docs
        system_docs = sb.table("knowledge_documents").select("*").eq("scope", "system").execute().data or []

        # User docs
        uq = (
            sb.table("knowledge_documents")
            .select("*")
            .eq("scope", "user")
            .eq("user_id", user_id)
        )
        if brand_id:
            uq = uq.eq("brand_id", brand_id)
        user_docs = uq.order("created_at", desc=True).execute().data or []

        all_docs = system_docs + user_docs

        # Filter by agent scope (if agent_id provided, include docs with [] scope or matching agent_id)
        if agent_id:
            filtered = []
            for doc in all_docs:
                agent_scope = doc.get("agent_scope") or []
                if not agent_scope or agent_id in agent_scope:
                    filtered.append(doc)
            all_docs = filtered

        # Format as plain text for prompt injection
        formatted = []
        for doc in all_docs:
            scope_label = "[SYSTEM SOP]" if doc.get("scope") == "system" else "[YOUR DOC]"
            platform_label = f"[{doc.get('platform', 'all').upper()}]"
            formatted.append(
                f"## {scope_label} {platform_label} {doc['title']}\n{doc['content']}"
            )

        return {
            "docs": [_row_to_response(d) for d in all_docs],
            "formatted": "\n\n---\n\n".join(formatted),
            "count": len(all_docs),
        }

    except Exception as exc:
        logger.warning("get_knowledge_docs_for_agent failed: %s", exc)
        return {"docs": [], "formatted": "", "count": 0}
