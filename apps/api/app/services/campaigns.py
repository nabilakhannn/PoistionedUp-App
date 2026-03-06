"""Campaign Service — Slice 108.

Manages the campaign lifecycle: create, update, track progress, execute sequentially.
Campaigns have priority over autonomous pipeline — user-planned content runs first.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("app.services.campaigns")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value))


# ── CRUD ─────────────────────────────────────────────────────────────


def create_campaign(
    user_id: str,
    brand_id: str,
    name: str,
    description: str = "",
    platforms: Optional[list] = None,
    content_types: Optional[list] = None,
    total_pieces: int = 5,
    template_id: Optional[str] = None,
) -> dict:
    """Create a new campaign in planning status."""
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(brand_id):
        raise ValueError("Invalid user_id or brand_id")

    from app.deps import get_admin_client
    sb = get_admin_client()

    row = {
        "user_id": user_id,
        "brand_id": brand_id,
        "name": name.strip()[:200],
        "description": description.strip()[:1000],
        "platforms": platforms or ["linkedin"],
        "content_types": content_types or ["text"],
        "total_pieces": max(1, min(total_pieces, 100)),
        "template_id": template_id,
        "status": "planning",
    }

    result = sb.table("campaigns").insert(row).execute()
    if not result.data:
        raise RuntimeError("Failed to create campaign")
    return result.data[0]


def list_campaigns(user_id: str, brand_id: Optional[str] = None) -> list:
    """List campaigns for a user, optionally filtered by brand."""
    if not _is_valid_uuid(user_id):
        return []

    from app.deps import get_admin_client
    sb = get_admin_client()

    query = sb.table("campaigns").select("*").eq("user_id", user_id)
    if brand_id and _is_valid_uuid(brand_id):
        query = query.eq("brand_id", brand_id)
    query = query.order("created_at", desc=True)
    result = query.execute()
    return result.data or []


def get_campaign(user_id: str, campaign_id: str) -> Optional[dict]:
    """Get a single campaign by ID (with user IDOR guard)."""
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(campaign_id):
        return None

    from app.deps import get_admin_client
    sb = get_admin_client()

    result = (
        sb.table("campaigns")
        .select("*")
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def update_campaign(user_id: str, campaign_id: str, updates: dict) -> Optional[dict]:
    """Update campaign fields (name, description, status, pieces counts)."""
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(campaign_id):
        return None

    from app.deps import get_admin_client
    sb = get_admin_client()

    allowed = {"name", "description", "status", "total_pieces", "completed_pieces", "approved_pieces", "platforms", "content_types"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return None

    result = (
        sb.table("campaigns")
        .update(filtered)
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def delete_campaign(user_id: str, campaign_id: str) -> bool:
    """Delete a campaign."""
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(campaign_id):
        return False

    from app.deps import get_admin_client
    sb = get_admin_client()

    result = (
        sb.table("campaigns")
        .delete()
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)


# ── Campaign Execution ───────────────────────────────────────────────


def get_active_campaigns(brand_id: str) -> list:
    """Get all active campaigns for a brand (for pipeline priority)."""
    if not _is_valid_uuid(brand_id):
        return []

    from app.deps import get_admin_client
    sb = get_admin_client()

    result = (
        sb.table("campaigns")
        .select("*")
        .eq("brand_id", brand_id)
        .eq("status", "active")
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def increment_completed(user_id: str, campaign_id: str) -> Optional[dict]:
    """Increment completed_pieces. If total reached, mark as done."""
    campaign = get_campaign(user_id, campaign_id)
    if not campaign:
        return None

    new_completed = campaign["completed_pieces"] + 1
    updates = {"completed_pieces": new_completed}
    if new_completed >= campaign["total_pieces"]:
        updates["status"] = "done"

    return update_campaign(user_id, campaign_id, updates)


def increment_approved(user_id: str, campaign_id: str) -> Optional[dict]:
    """Increment approved_pieces."""
    campaign = get_campaign(user_id, campaign_id)
    if not campaign:
        return None

    return update_campaign(user_id, campaign_id, {
        "approved_pieces": campaign["approved_pieces"] + 1,
    })


def has_pending_campaign_work(brand_id: str) -> bool:
    """Check if any active campaigns have incomplete pieces.

    Used by jumbo_pipeline to prioritize campaign content over autonomous pipeline.
    """
    campaigns = get_active_campaigns(brand_id)
    return any(c["completed_pieces"] < c["total_pieces"] for c in campaigns)
