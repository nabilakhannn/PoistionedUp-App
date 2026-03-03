"""Personal Brands CRUD router.

Endpoints for creating, listing, updating, and deleting personal brands.
Each user can have multiple personal brands. Content generation, chats,
workflows, and memory are all scoped to a selected brand.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

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
    """Run the next research stage.

    Query params:
      - run_all: bool = false — ignored (kept for backwards compat).
        Running all stages in one request exceeds Vercel's serverless timeout.
        The frontend runs stages one at a time.
    """
    from app.services.brand_research import run_stage, STAGES, STAGE_LABELS

    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    try:
        # Always run one stage at a time — run_all would timeout on serverless
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


# ── Zero-Setup Auto-Profile (Slice 91b) ──────────────────────────────────────

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9 '\-\.\,]")

_AUTO_PROFILE_SYSTEM = """You are a brand strategist extracting a personal brand profile from web research.

Given snippets about a person, extract a structured brand profile.
Return ONLY valid JSON — no other text:

{
  "foundation": {
    "content_pillars": ["topic1", "topic2", "topic3"],
    "beliefs": ["They believe...", "They stand for..."]
  },
  "ica": {
    "demographics": {"occupation": "...", "pain": "..."},
    "big_need": "...",
    "big_want": "..."
  },
  "offer": {
    "what": "...",
    "target_audience": "...",
    "differentiator": "..."
  },
  "positioning": {
    "unique_angle": "...",
    "voice_tone": "...",
    "key_topics": ["...", "..."]
  },
  "summary": "One sentence: what they do and who they serve."
}

Rules:
- Extract only what's clearly supported by the research — don't invent details
- content_pillars: 3-5 topics they clearly cover (not generic: real specific topics from their content)
- beliefs: what principles/opinions they visibly stand for
- If information is missing, use "" for strings and [] for lists — don't guess
- summary: "<Name> helps <audience> to <outcome> through <method>"
"""


class AutoProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    public_url: str = ""        # LinkedIn, website, X/Twitter — any public URL
    extra_context: str = ""     # "I'm a SaaS founder who teaches..."


def _search_perplexity(query: str, api_key: str) -> str:
    """Call Perplexity for web research. Returns text snippets."""
    try:
        resp = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1500,
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Perplexity search failed: %s", exc)
        return ""


def _search_tavily(query: str, api_key: str) -> str:
    """Tavily fallback for web research."""
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": 6},
            timeout=15.0,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:400]}"
            for r in results
        )
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return ""


def _synthesize_profile(research_text: str, full_name: str, extra_context: str) -> Optional[Dict]:
    """Use Claude Sonnet 4.6 to extract a brand profile from web research."""
    from app.config import settings
    if not settings.anthropic_api_key:
        return None

    user_msg = f"Person: {full_name}\n\nResearch findings:\n{research_text[:6000]}"
    if extra_context:
        user_msg += f"\n\nAdditional context they provided: {extra_context[:500]}"
    user_msg += "\n\nExtract the brand profile JSON."

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_AUTO_PROFILE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Profile synthesis failed: %s", exc)
        return None


def _save_profile_sections(admin, brand_id: str, user_id: str, profile: Dict) -> List[str]:
    """Deep-merge extracted profile into brand profile_json. Only fills empty fields."""
    row = _get_brand_profile_json(admin, brand_id, user_id)
    existing = row if isinstance(row, dict) else {}
    sections_filled = []

    def _is_empty(val) -> bool:
        if val is None: return True
        if isinstance(val, (str,)) and not val.strip(): return True
        if isinstance(val, (list, dict)) and not val: return True
        return False

    for section, new_data in profile.items():
        if section == "summary":
            continue
        if not isinstance(new_data, dict):
            continue
        current = existing.get(section, {})
        if not isinstance(current, dict):
            current = {}
        merged = dict(current)
        updated = False
        for key, value in new_data.items():
            if _is_empty(current.get(key)) and not _is_empty(value):
                merged[key] = value
                updated = True
        if updated:
            try:
                _update_brand_profile_section(admin, brand_id, user_id, section, merged)
                sections_filled.append(section)
            except Exception as exc:
                logger.warning("Failed to save section %s: %s", section, exc)

    return sections_filled


@router.post("/{brand_id}/auto-profile")
async def auto_profile_brand(
    brand_id: str,
    body: AutoProfileRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Zero-Setup Onboarding — Slice 91b.

    Takes a name + optional public URL → Perplexity finds their public content
    → Claude extracts brand profile → saves to profile_json (only fills empty fields).

    Works in < 30 seconds. Gracefully degrades if no search keys are configured.
    Returns: { ok, sections_filled, summary, data_found }
    """
    from app.config import settings

    admin = get_admin_client()
    _verify_brand_ownership(admin, brand_id, user.id)

    # Sanitize name (strip injection chars, keep letters/spaces/hyphens/etc.)
    safe_name = _SAFE_NAME_RE.sub("", body.full_name).strip()[:100]
    if not safe_name:
        raise HTTPException(400, "full_name contains invalid characters")

    # Validate public_url (SSRF protection — validate but never fetch directly)
    safe_url = ""
    if body.public_url.strip():
        try:
            from app.utils.url_validation import validate_url
            safe_url = validate_url(body.public_url.strip())
        except Exception:
            safe_url = ""  # Invalid URL — ignore silently

    # Build search query
    url_hint = f" site:{safe_url.split('/')[2]}" if safe_url else ""
    query = (
        f'"{safe_name}" content creator OR expert posts LinkedIn{url_hint} '
        f"what they teach audience topics"
    )
    if body.extra_context:
        query += f" context: {body.extra_context[:200]}"

    # Step 1: Research via Perplexity → Tavily fallback
    research_text = ""
    data_found = False

    if settings.perplexity_api_key:
        research_text = _search_perplexity(query, settings.perplexity_api_key)
    if not research_text and settings.tavily_api_key:
        research_text = _search_tavily(query, settings.tavily_api_key)

    if research_text:
        data_found = True

    # Add extra_context to research text even if search failed
    if body.extra_context and not research_text:
        research_text = f"Self-described: {body.extra_context}"
        data_found = False  # No external data found

    # Step 2: Synthesize profile with Claude
    profile = None
    summary = ""
    if research_text:
        profile = _synthesize_profile(research_text, safe_name, body.extra_context)
        if profile:
            summary = profile.pop("summary", "")

    # Fallback: save extra_context as a belief if nothing else worked
    sections_filled: List[str] = []
    if not profile and body.extra_context:
        try:
            row = _get_brand_profile_json(admin, brand_id, user.id)
            existing = row if isinstance(row, dict) else {}
            current_beliefs = existing.get("foundation", {}).get("beliefs", [])
            if not current_beliefs:
                _update_brand_profile_section(admin, brand_id, user.id, "foundation", {
                    "beliefs": [body.extra_context.strip()[:500]],
                })
                sections_filled = ["foundation"]
        except Exception as exc:
            logger.warning("Fallback save failed: %s", exc)
    elif profile:
        sections_filled = _save_profile_sections(admin, brand_id, user.id, profile)

    track_event(user.id, "auto_profile_run", {
        "brand_id": brand_id,
        "data_found": data_found,
        "sections_filled": len(sections_filled),
    })

    logger.info(
        "Auto-profile: user=%s brand=%s data_found=%s sections=%s",
        user.id, brand_id, data_found, sections_filled,
    )

    return {
        "ok": True,
        "sections_filled": sections_filled,
        "summary": summary,
        "data_found": data_found,
    }
