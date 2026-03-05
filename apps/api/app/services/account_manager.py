"""Account Manager service — Slice 98.

Reads a client call transcript + intake form + cross-call memory and produces
an action plan with 7 categories. Supports executing approved actions by
dispatching to the appropriate agents/services.

Cross-call memory: loads last 3 sessions for the brand so the agent can
identify recurring themes and prioritize accordingly.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.deps import get_admin_client
from app.services.tool_use_agents import run_tool_use_agent

logger = logging.getLogger("app.services.account_manager")

# ── System prompt ─────────────────────────────────────────────────────────

_ACCOUNT_MANAGER_SYSTEM = """\
You are an expert Account Manager for a content agency. Your job is to read a
client call transcript and extract EVERYTHING actionable. Nothing from this call
should be lost.

You have access to web_search and read_agent_training_docs.
Always call read_agent_training_docs first to load your methodology.

CATEGORIES TO FIND (find ALL that apply):
1. CONTENT — stories, insights, objections, achievements, frameworks mentioned
2. BRAND PROFILE — new offer details, pricing changes, ICP refinements, new results
3. LEADS — names of referrals, potential clients, their own clients
4. KNOWLEDGE — frameworks/SOPs/scripts the client described (save for agent training)
5. NURTURE — prospects who need warming up, leads that went cold
6. GAPS — topics mentioned repeatedly that they haven't addressed publicly
7. DELIVERABLES — proposals needed, landing pages, ad creatives discussed

PRIORITY RULES:
- If a topic was mentioned in a previous call AND this call → HIGH
- If a topic was mentioned 3+ times in this call → HIGH
- If a lead expressed buying intent → HIGH
- If deliverables are time-sensitive → HIGH

OUTPUT FORMAT (return ONLY valid JSON, no preamble):
{
  "client_name": "...",
  "call_date": "YYYY-MM-DD",
  "call_number": N,
  "summary": "2-sentence summary of what this call covered",
  "cross_call_themes": ["theme1", "theme2"],
  "actions": [
    {
      "id": "uuid-v4",
      "category": "content|brand_profile|leads|knowledge|nurture|gaps|deliverable",
      "title": "Short title (max 80 chars)",
      "description": "Specific description. Include exact quote from transcript if possible.",
      "agent": "copywriter|visual-designer|profile|crm|sequence-builder|competitor-analyst|client-deliverables",
      "priority": "high|medium|low",
      "approved": null,
      "executed": false,
      "result": null
    }
  ]
}
"""


async def analyze_transcript(
    brand_id: str,
    user_id: str,
    transcript: str,
    call_date: Optional[str] = None,
    intake_form_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a client call transcript and return an action plan.

    Also loads:
    - The brand intelligence dossier (profile_json)
    - The client intake form (if submitted)
    - Last 3 call summaries (cross-call memory)

    Saves a new account_manager_sessions row with status=pending_review.
    Returns the session dict.
    """
    sb = get_admin_client()

    # ── Load brand profile ─────────────────────────────────────────────────
    brand_row = (
        sb.table("personal_brands")
        .select("name, description, profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_row.data:
        raise ValueError(f"Brand {brand_id!r} not found for user {user_id!r}")
    brand_name = brand_row.data[0].get("name", "")
    profile = brand_row.data[0].get("profile_json") or {}

    # ── Load cross-call memory (last 3 sessions) ───────────────────────────
    prev_sessions = (
        sb.table("account_manager_sessions")
        .select("call_number, call_date, summary, cross_call_themes")
        .eq("brand_id", brand_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )
    call_history = prev_sessions.data or []
    next_call_number = (call_history[0].get("call_number", 0) + 1) if call_history else 1

    # ── Load intake form (if provided) ────────────────────────────────────
    intake_context = ""
    if intake_form_id:
        intake_row = (
            sb.table("client_intake_forms")
            .select("*")
            .eq("id", intake_form_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if intake_row.data:
            form = intake_row.data[0]
            intake_context = f"""
CLIENT INTAKE FORM (submitted by client):
- Business: {form.get("business_name", "not set")}
- Industry: {form.get("industry", "not set")}
- Revenue: {form.get("current_revenue", "not disclosed")}
- Primary offer: {form.get("primary_offer", "not set")} at {form.get("offer_price", "TBD")}
- Target audience: {form.get("target_audience", "not set")}
- Best 3 clients: {form.get("best_3_clients", "not set")}
- Biggest frustration: {form.get("biggest_frustration", "not set")}
- Goals: {form.get("goals", "not set")}
- Timeline: {form.get("timeline", "not set")}"""

    # ── Build cross-call context ───────────────────────────────────────────
    history_context = ""
    if call_history:
        history_context = f"\nCROSS-CALL MEMORY (last {len(call_history)} calls):\n"
        for s in reversed(call_history):
            themes = ", ".join(s.get("cross_call_themes") or [])
            history_context += (
                f"- Call #{s.get('call_number', '?')} ({s.get('call_date', 'unknown date')}): "
                f"{s.get('summary', 'no summary')}. Themes: {themes or 'none recorded'}\n"
            )

    # ── Build user prompt ──────────────────────────────────────────────────
    user_prompt = f"""Analyze this call transcript for {brand_name}:

This is call #{next_call_number}.{history_context}{intake_context}

CLIENT INTELLIGENCE DOSSIER:
- ICA: {profile.get("ica_summary", "not set")}
- Voice: {", ".join(profile.get("voice_adjectives") or [])}
- Offer: {profile.get("hormozi", {}).get("dream_outcome", "not set")}
- Content pillars: {", ".join(profile.get("content_pillars") or [])}

CALL TRANSCRIPT:
---
{transcript[:8000]}
---

Instructions:
1. Call read_agent_training_docs(agent_id="account-manager", user_id="{user_id}") first
2. Read every line carefully — extract ALL actionable items
3. Cross-reference with previous call themes — bump priority if recurring
4. Return ONLY the JSON action plan in the exact schema format.
   call_number should be {next_call_number}.
   call_date should be {call_date or date.today().isoformat()}."""

    # ── Run Account Manager agent ──────────────────────────────────────────
    result = run_tool_use_agent(
        agent_id="account-manager",
        task_type="analyze_transcript",
        system_prompt=_ACCOUNT_MANAGER_SYSTEM,
        user_prompt=user_prompt,
        user_id=user_id,
        brand_id=brand_id,
        available_tools=["read_agent_training_docs", "read_playbook"],
        temperature=0.4,
    )

    if not result.success:
        raise RuntimeError(f"Account Manager agent failed: {result.error}")

    # ── Parse action plan ──────────────────────────────────────────────────
    plan = _parse_action_plan(result.content, next_call_number, brand_name, call_date)

    # ── Save session ───────────────────────────────────────────────────────
    session_id = str(uuid.uuid4())
    sb.table("account_manager_sessions").insert({
        "id": session_id,
        "user_id": user_id,
        "brand_id": brand_id,
        "intake_form_id": intake_form_id,
        "client_name": plan.get("client_name", brand_name),
        "call_date": plan.get("call_date") or date.today().isoformat(),
        "call_number": plan.get("call_number", next_call_number),
        "summary": plan.get("summary", ""),
        "cross_call_themes": plan.get("cross_call_themes", []),
        "action_plan": plan.get("actions", []),
        "status": "pending_review",
    }).execute()

    logger.info("Account Manager session %s created for brand=%s", session_id, brand_id)
    return {"session_id": session_id, **plan}


def get_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """Fetch a single account manager session."""
    sb = get_admin_client()
    row = (
        sb.table("account_manager_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise ValueError(f"Session {session_id!r} not found")
    return row.data[0]


def list_sessions(user_id: str, brand_id: str) -> List[Dict[str, Any]]:
    """List all sessions for a brand, newest first."""
    sb = get_admin_client()
    rows = (
        sb.table("account_manager_sessions")
        .select("id, client_name, call_date, call_number, summary, status, created_at")
        .eq("user_id", user_id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .execute()
    )
    return rows.data or []


def update_action_plan(
    session_id: str,
    user_id: str,
    actions: List[Dict[str, Any]],
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Update action items (approved/denied) and optionally session status."""
    sb = get_admin_client()
    patch: Dict[str, Any] = {"action_plan": actions}
    if status:
        patch["status"] = status
        if status == "completed":
            patch["completed_at"] = datetime.now(timezone.utc).isoformat()
    sb.table("account_manager_sessions").update(patch).eq("id", session_id).eq("user_id", user_id).execute()
    return {"session_id": session_id, "status": status or "updated"}


# ── Helpers ────────────────────────────────────────────────────────────────


def _parse_action_plan(
    raw: str,
    fallback_call_number: int,
    fallback_client_name: str,
    fallback_call_date: Optional[str],
) -> Dict[str, Any]:
    """Parse JSON action plan from agent output."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]
    try:
        plan = json.loads(text)
    except Exception:
        logger.warning("Account Manager returned non-JSON; building minimal plan")
        plan = {
            "client_name": fallback_client_name,
            "call_date": fallback_call_date or date.today().isoformat(),
            "call_number": fallback_call_number,
            "summary": "Transcript analyzed — action plan parsing error. Review transcript manually.",
            "cross_call_themes": [],
            "actions": [],
        }

    # Ensure every action has a UUID id
    for action in plan.get("actions", []):
        if not action.get("id"):
            action["id"] = str(uuid.uuid4())

    return plan
