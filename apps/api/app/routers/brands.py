"""Personal Brands CRUD router.

Endpoints for creating, listing, updating, and deleting personal brands.
Each user can have multiple personal brands. Content generation, chats,
workflows, and memory are all scoped to a selected brand.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.personal_brands import (
    ModelTierInfo,
    ModelTierListResponse,
    PersonalBrandCreate,
    PersonalBrandDetail,
    PersonalBrandListResponse,
    PersonalBrandSummary,
    PersonalBrandUpdate,
)
from app.services.analytics import track_event
from app.services.brand_chat import calculate_completeness
from worker.graph.llm import MODEL_TIERS, VALID_TIERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brands", tags=["brands"])


# ── Helpers ──────────────────────────────────────────────────

MAX_BRANDS_PER_USER = 10


def _verify_brand_ownership(admin, brand_id: str, user_id: str) -> Dict[str, Any]:
    """Fetch a brand row and verify that it belongs to the user. Returns the row or raises 404."""
    resp = (
        admin.table("personal_brands")
        .select("*")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )
    return resp.data[0]


# ── CRUD ─────────────────────────────────────────────────────


@router.get("/model-tiers", response_model=ModelTierListResponse)
async def get_model_tiers(
    brand_id: str = "",
    user: CurrentUser = Depends(get_current_user),
):
    """Get available model tiers with pricing info.

    If brand_id is provided, includes the brand's current tier.
    """
    current_tier = "budget"
    if brand_id:
        admin = get_admin_client()
        row = _verify_brand_ownership(admin, brand_id, user.id)
        current_tier = row.get("model_tier", "budget")

    tiers = []
    for key, info in MODEL_TIERS.items():
        tiers.append(ModelTierInfo(
            key=key,
            label=info["label"],
            description=info["description"],
            creative_model=info["creative"],
            review_model=info["review"],
            provider=info["provider"],
            est_cost_per_workflow=info["est_cost_per_workflow"],
            est_cost_per_chat_msg=info["est_cost_per_chat_msg"],
        ))

    return ModelTierListResponse(tiers=tiers, current_tier=current_tier)


@router.get("", response_model=PersonalBrandListResponse)
async def list_brands(
    user: CurrentUser = Depends(get_current_user),
):
    """List all personal brands for the current user."""
    admin = get_admin_client()

    resp = (
        admin.table("personal_brands")
        .select("id, name, description, is_active, model_tier, profile_json, created_at, updated_at")
        .eq("user_id", user.id)
        .order("created_at", desc=False)
        .execute()
    )

    brands = []
    for row in resp.data or []:
        profile = row.get("profile_json", {}) or {}
        completeness = calculate_completeness(profile)
        brands.append(PersonalBrandSummary(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            is_active=row.get("is_active", True),
            model_tier=row.get("model_tier", "budget"),
            completeness=completeness,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        ))

    return PersonalBrandListResponse(brands=brands, total=len(brands))


@router.post("", response_model=PersonalBrandDetail, status_code=status.HTTP_201_CREATED)
async def create_brand(
    body: PersonalBrandCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new personal brand."""
    admin = get_admin_client()

    # Check brand limit
    count_resp = (
        admin.table("personal_brands")
        .select("id", count="exact")
        .eq("user_id", user.id)
        .execute()
    )
    current_count = count_resp.count if hasattr(count_resp, "count") and count_resp.count is not None else len(count_resp.data or [])
    if current_count >= MAX_BRANDS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {MAX_BRANDS_PER_USER} brands per account.",
        )

    insert_data = {
        "user_id": user.id,
        "name": body.name,
        "description": body.description,
        "profile_json": {},
        "is_active": True,
    }
    if body.model_tier and body.model_tier in VALID_TIERS:
        insert_data["model_tier"] = body.model_tier

    resp = (
        admin.table("personal_brands")
        .insert(insert_data)
        .execute()
    )

    row = resp.data[0]

    # Track brand creation
    track_event(user.id, "brand_created", {
        "brand_id": row["id"],
        "brand_name": row["name"],
        "model_tier": row.get("model_tier", "budget"),
    })

    return PersonalBrandDetail(
        id=row["id"],
        name=row["name"],
        description=row.get("description"),
        is_active=row.get("is_active", True),
        model_tier=row.get("model_tier", "budget"),
        profile_json=row.get("profile_json", {}),
        completeness=calculate_completeness({}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{brand_id}", response_model=PersonalBrandDetail)
async def get_brand(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single personal brand with full profile data."""
    admin = get_admin_client()
    row = _verify_brand_ownership(admin, brand_id, user.id)

    profile = row.get("profile_json", {}) or {}
    return PersonalBrandDetail(
        id=row["id"],
        name=row["name"],
        description=row.get("description"),
        is_active=row.get("is_active", True),
        model_tier=row.get("model_tier", "budget"),
        profile_json=profile,
        completeness=calculate_completeness(profile),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/{brand_id}", response_model=PersonalBrandDetail)
async def update_brand(
    brand_id: str,
    body: PersonalBrandUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update a personal brand's name, description, or active status."""
    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if body.model_tier is not None:
        if body.model_tier not in VALID_TIERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid model tier. Must be one of: %s" % ", ".join(VALID_TIERS),
            )
        updates["model_tier"] = body.model_tier

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    resp = (
        admin.table("personal_brands")
        .update(updates)
        .eq("id", brand_id)
        .eq("user_id", user.id)
        .execute()
    )

    row = resp.data[0]
    profile = row.get("profile_json", {}) or {}

    track_event(user.id, "brand_updated", {
        "brand_id": brand_id,
        "fields_updated": list(updates.keys()),
    })

    return PersonalBrandDetail(
        id=row["id"],
        name=row["name"],
        description=row.get("description"),
        is_active=row.get("is_active", True),
        model_tier=row.get("model_tier", "budget"),
        profile_json=profile,
        completeness=calculate_completeness(profile),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Soft-delete a personal brand (set is_active=false).

    Does not delete associated chats, workflows, or content.
    """
    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    admin.table("personal_brands").update({
        "is_active": False,
    }).eq("id", brand_id).eq("user_id", user.id).execute()

    track_event(user.id, "brand_deleted", {"brand_id": brand_id})

    return {"message": "Brand deactivated"}


# ── Brand Profile Sub-Endpoints ──────────────────────────────
# These read/write from personal_brands.profile_json instead of
# the old profiles.profile_json.


def _get_brand_profile_json(admin, brand_id: str, user_id: str) -> Dict[str, Any]:
    """Fetch profile_json from a personal brand."""
    row = _verify_brand_ownership(admin, brand_id, user_id)
    return row.get("profile_json", {}) or {}


def _update_brand_profile_section(admin, brand_id: str, user_id: str, section: str, data: Dict[str, Any]):
    """Update a specific section within a brand's profile_json."""
    from app.services.brand_chat import deep_merge

    current = _get_brand_profile_json(admin, brand_id, user_id)
    current_section = current.get(section, {})
    merged = deep_merge(current_section, data)
    current[section] = merged

    admin.table("personal_brands").update({
        "profile_json": current,
    }).eq("id", brand_id).eq("user_id", user_id).execute()

    return merged


@router.patch("/{brand_id}/foundation")
async def update_brand_foundation(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Foundation fields for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "foundation", body)
    return {"message": "Foundation updated", "foundation": merged}


@router.patch("/{brand_id}/ica")
async def update_brand_ica(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update ICA fields for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "ica", body)
    return {"message": "ICA updated", "ica": merged}


@router.patch("/{brand_id}/offer")
async def update_brand_offer(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Offer fields for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "offer", body)
    return {"message": "Offer updated", "offer": merged}


@router.patch("/{brand_id}/statement")
async def update_brand_statement(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Brand Statement for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "brand", body)
    return {"message": "Brand statement updated", "brand": merged}


@router.patch("/{brand_id}/authority")
async def update_brand_authority(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Authority Building fields for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "authority", body)
    return {"message": "Authority updated", "authority": merged}


@router.patch("/{brand_id}/messaging")
async def update_brand_messaging(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Messaging fields for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "messaging", body)
    return {"message": "Messaging updated", "messaging": merged}


@router.patch("/{brand_id}/positioning")
async def update_brand_positioning(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Positioning fields for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "positioning", body)
    return {"message": "Positioning updated", "positioning": merged}


@router.patch("/{brand_id}/competitors")
async def update_brand_competitors(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Competitors fields for a specific brand."""
    admin = get_admin_client()
    merged = _update_brand_profile_section(admin, brand_id, user.id, "competitors", body)
    return {"message": "Competitors updated", "competitors": merged}


@router.get("/{brand_id}/completeness")
async def get_brand_completeness(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get completion percentage for each brand module."""
    admin = get_admin_client()
    profile = _get_brand_profile_json(admin, brand_id, user.id)
    return calculate_completeness(profile)


# ── Brand Research Pipeline ───────────────────────────────────


@router.post("/{brand_id}/research")
async def start_brand_research(
    brand_id: str,
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Start an automated brand research pipeline.

    Body requires at minimum:
      - industry: str (the niche/industry)

    Optional:
      - name: str (person's name, defaults to brand name)
      - description: str (what they do)
      - target_audience: str (who they serve)

    Returns the research session with status "pending".
    """
    from app.services.brand_research import create_session, STAGES, STAGE_LABELS

    admin = get_admin_client()
    row = _verify_brand_ownership(admin, brand_id, user.id)

    industry = (body.get("industry") or "").strip()
    if not industry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="industry is required",
        )

    seed_input = {
        "name": body.get("name", row.get("name", "")),
        "industry": industry,
        "description": body.get("description", row.get("description", "")),
        "target_audience": body.get("target_audience", ""),
    }

    session = create_session(user.id, brand_id, seed_input)

    track_event(user.id, "brand_research_started", {
        "brand_id": brand_id,
        "session_id": session["id"],
        "industry": industry,
    })

    return {
        **session,
        "stages": STAGES,
        "stage_labels": STAGE_LABELS,
    }


@router.get("/{brand_id}/research")
async def list_brand_research(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """List all research sessions for a brand."""
    from app.services.brand_research import get_sessions_for_brand, STAGES, STAGE_LABELS

    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    sessions = get_sessions_for_brand(user.id, brand_id)
    return {
        "sessions": sessions,
        "stages": STAGES,
        "stage_labels": STAGE_LABELS,
    }


@router.get("/{brand_id}/research/{session_id}")
async def get_brand_research(
    brand_id: str,
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a specific research session with full results."""
    from app.services.brand_research import get_session, STAGES, STAGE_LABELS

    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    session = get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    return {
        **session,
        "stages": STAGES,
        "stage_labels": STAGE_LABELS,
    }


@router.post("/{brand_id}/research/{session_id}/run")
async def run_research_stage(
    brand_id: str,
    session_id: str,
    run_all: bool = False,
    user: CurrentUser = Depends(get_current_user),
):
    """Run the next research stage (or all remaining stages).

    Query params:
      - run_all: bool = false — if true, runs all remaining stages sequentially
    """
    from app.services.brand_research import run_stage, run_all_stages, STAGES, STAGE_LABELS

    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    try:
        if run_all:
            session = run_all_stages(session_id, user.id)
        else:
            session = run_stage(session_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Research stage failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Research stage failed. Check the session status for details.",
        )

    return {
        **session,
        "stages": STAGES,
        "stage_labels": STAGE_LABELS,
    }


@router.post("/{brand_id}/research/{session_id}/skip")
async def skip_research_stage(
    brand_id: str,
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Skip the current failed/pending research stage and advance to the next one."""
    from app.services.brand_research import skip_stage, STAGES, STAGE_LABELS

    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    try:
        session = skip_stage(session_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        **session,
        "stages": STAGES,
        "stage_labels": STAGE_LABELS,
    }


@router.post("/{brand_id}/research/{session_id}/apply")
async def apply_research_to_brand(
    brand_id: str,
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Apply completed research results to pre-fill brand profile fields.

    Only fills empty fields. Never overwrites user-entered data.
    Returns the list of fields that were pre-filled.
    """
    from app.services.brand_research import apply_research_to_profile

    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    try:
        prefilled = apply_research_to_profile(session_id, user.id, brand_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    track_event(user.id, "brand_research_applied", {
        "brand_id": brand_id,
        "session_id": session_id,
        "fields_prefilled": len(prefilled),
    })

    return {
        "message": f"Pre-filled {len(prefilled)} fields from research",
        "prefilled_fields": prefilled,
    }
