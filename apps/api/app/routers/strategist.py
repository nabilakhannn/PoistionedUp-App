"""Brand Strategist v2 API router.

Agentic brand coaching conversation (Slice 63):
  POST /brand/strategist/chat                - Send a message, get structured JSON responses
  GET  /brand/strategist/completeness/{id}   - Field-level completeness for a brand
  GET  /brand/strategist/next-field/{id}     - Next recommended field from sequencing engine
  POST /brand/strategist/save-field          - Explicitly save a field value
  POST /brand/strategist/chat/{id}/resume    - Resume existing chat (returns structured responses)
  POST /brand/strategist/chat/{id}/new       - Start a fresh strategist chat
  GET  /brand/strategist/chat/history        - Get raw chat history (backward compat)

KEY CHANGES (Slice 63):
- REMOVED response_format={"type": "json_object"} -- lets the model think and reason
- Conversation history transformed to natural text before LLM call
- Robust parser handles mixed text+JSON responses
- Safety net auto-chains next question if LLM forgets
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.strategist import (
    FieldCompletenessResponse,
    NextFieldResponse,
    StrategistChatRequest,
    StrategistChatResponse,
)
from app.services.brand_strategist import (
    build_resume_responses,
    build_strategist_messages,
    fetch_all_context,
    get_welcome_with_first_question,
    parse_strategist_response,
    save_field_to_profile,
    save_fields_from_responses,
)
from app.services.brand_sequencing import (
    calculate_field_completeness,
    get_filled_fields,
    get_next_field,
    get_transition_message,
)
from app.services.brand_fields import get_field, MODULE_LABELS

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/brand/strategist", tags=["strategist"])


# -- Helpers ----------------------------------------------------------


def _get_llm_client():
    """Get the LLM client (lazy import to avoid circular deps)."""
    from worker.graph.llm import get_llm_client
    return get_llm_client()


def _get_brand_row(admin, brand_id: str, user_id: str) -> Dict[str, Any]:
    """Fetch and validate a personal brand row."""
    resp = (
        admin.table("personal_brands")
        .select("id, user_id, profile_json, name, model_tier")
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


def _get_or_create_strategist_chat(
    admin, user_id: str, brand_id: str, profile_json: Dict[str, Any],
) -> Dict[str, Any]:
    """Find the active strategist chat or create one."""
    query = (
        admin.table("brand_chats")
        .select("*")
        .eq("user_id", user_id)
        .eq("brand_id", brand_id)
        .eq("module", "strategist")
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
    )
    resp = query.execute()

    if resp.data:
        return resp.data[0]

    # New chat: generate welcome + first question
    filled = get_filled_fields(profile_json)

    if len(filled) == 0:
        welcome_responses = get_welcome_with_first_question()
        opening_content = json.dumps(welcome_responses)
    else:
        next_f = get_next_field(profile_json)
        resume_responses = build_resume_responses(profile_json, next_f)
        opening_content = json.dumps(resume_responses)

    opening_messages = [
        {"role": "assistant", "content": opening_content},
    ]

    insert_data = {
        "user_id": user_id,
        "brand_id": brand_id,
        "module": "strategist",
        "messages": opening_messages,
        "extracted": {},
        "status": "active",
        "title": "Brand Strategy Session",
    }

    new_chat = admin.table("brand_chats").insert(insert_data).execute()
    return new_chat.data[0]


def _parse_last_assistant_responses(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Parse the last assistant message into structured response objects."""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            return parse_strategist_response(content)

    return [{"type": "message", "message": "Let us continue building your brand."}]


# -- POST /brand/strategist/chat ---------------------------------------


@router.post("/chat", response_model=StrategistChatResponse)
async def strategist_chat(
    body: StrategistChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message to the brand strategist.

    The strategist responds with structured JSON: options, refinement,
    save, message, or content. Multiple response objects can be returned
    in a single turn (e.g., save + next question).
    """
    admin = get_admin_client()

    # Validate brand ownership
    brand_row = _get_brand_row(admin, body.brand_id, user.id)
    profile_json = brand_row.get("profile_json") or {}

    # Find or create the strategist chat
    chat_row = _get_or_create_strategist_chat(
        admin, user.id, body.brand_id, profile_json,
    )

    # Get existing messages
    messages = chat_row.get("messages", []) or []

    # Build user message with metadata
    user_content = body.message

    # Add action/selection metadata if present
    metadata_parts = []
    if body.selected_option:
        metadata_parts.append(
            f"[USER_ACTION: selected option {body.selected_option}]"
        )
    if body.action:
        metadata_parts.append(f"[USER_ACTION: {body.action}]")
    if body.target_field:
        metadata_parts.append(f"[TARGET_FIELD: {body.target_field}]")

    if metadata_parts:
        user_content = " ".join(metadata_parts) + "\n\n" + user_content

    # Append user message to conversation
    messages.append({"role": "user", "content": user_content})

    # Build document context from file attachments
    doc_context = ""
    if body.file_context:
        fname = body.file_name or "uploaded file"
        doc_context = (
            f"--- DOCUMENT_CONTEXT ---\n"
            f"File: {fname}\n\n"
            f"{body.file_context}\n"
            f"--- END ---"
        )

    # Get the next recommended field from sequencing engine
    next_field = get_next_field(
        profile_json, context_hint=body.message,
    )

    # Fetch all context layers
    context = fetch_all_context(
        user_id=user.id,
        user_message=body.message,
        profile_json=profile_json,
        brand_id=body.brand_id,
    )

    # Build LLM messages (conversation history is transformed to natural text)
    llm_messages = build_strategist_messages(
        profile_json=profile_json,
        conversation=messages,
        next_field=next_field,
        resource_context=context.get("resource", ""),
        performance_context=context.get("performance", ""),
        memory_context=context.get("memory", ""),
        research_context=context.get("research", ""),
        document_context=doc_context,
        user_id=user.id,
        brand_id=body.brand_id,
    )

    # Call LLM -- NO response_format constraint (let the model think)
    from worker.graph.llm import get_model_for_chat
    strategist_tier = brand_row.get("model_tier", "") or ""
    strategist_model = get_model_for_chat(strategist_tier)

    llm = _get_llm_client()
    try:
        response = llm.chat(
            messages=llm_messages,
            model=strategist_model,
            temperature=0.7,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM API quota exceeded. Please check your billing or switch to a lower-cost model tier.",
            )
        logger.exception("LLM call failed for strategist chat")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {error_msg[:200]}",
        )

    raw_content = response.get("content", "")

    # Parse the structured response (handles text+JSON, plain text, etc.)
    parsed_responses = parse_strategist_response(raw_content)

    # Process any save operations
    updated_profile, saved_keys = save_fields_from_responses(
        profile_json, parsed_responses,
    )

    # If fields were saved, update the brand profile in DB
    if saved_keys:
        admin.table("personal_brands").update({
            "profile_json": updated_profile,
        }).eq("id", body.brand_id).execute()

        profile_json = updated_profile
        logger.info(
            "Saved %d fields for brand %s: %s",
            len(saved_keys), body.brand_id, saved_keys,
        )

    # Enrich save responses with computed completeness
    completeness = calculate_field_completeness(profile_json)
    for resp_obj in parsed_responses:
        if resp_obj.get("type") == "save" and not resp_obj.get("completeness"):
            module_name = resp_obj.get("module", "")
            mod_data = completeness.get("modules", {}).get(module_name, {})
            resp_obj["completeness"] = {
                "module_name": module_name,
                "module_percent": mod_data.get("percent", 0),
                "overall_percent": completeness.get("overall_percent", 0),
            }

    # ── Safety net: auto-chain next question after save ──
    has_save = any(r.get("type") == "save" for r in parsed_responses)
    has_followup = any(
        r.get("type") in ("options", "refinement", "content") for r in parsed_responses
    )
    if has_save and not has_followup:
        # Clean up save messages: strip percentage dumps
        for resp_obj in parsed_responses:
            if resp_obj.get("type") == "save":
                msg = resp_obj.get("message", "")
                cleaned = re.sub(r"(?m)^.*?\d+%.*$", "", msg).strip()
                if not cleaned:
                    cleaned = "Got it. Moving on."
                resp_obj["message"] = cleaned

        # Re-calculate next field AFTER saves were applied
        auto_next = get_next_field(profile_json, context_hint=body.message)
        if auto_next:
            last_save_module = ""
            for r in reversed(parsed_responses):
                if r.get("type") == "save":
                    last_save_module = r.get("module", "")
                    break

            transition = get_transition_message(
                last_save_module, auto_next.module,
            )
            question_msg = auto_next.question
            if transition:
                question_msg = transition + " " + auto_next.question

            parsed_responses.append({
                "type": "options",
                "module": auto_next.module,
                "field": auto_next.key,
                "message": question_msg,
                "options": [],
                "allow_custom": True,
                "allow_skip": True,
            })
            logger.info(
                "Auto-chained next question: %s.%s",
                auto_next.module, auto_next.key,
            )

    # Append assistant reply to conversation (store raw for re-parsing)
    messages.append({"role": "assistant", "content": raw_content})

    # Track saved fields in extracted
    current_extracted = chat_row.get("extracted", {}) or {}
    if saved_keys:
        saved_set = set(current_extracted.get("saved_fields", []))
        saved_set.update(saved_keys)
        current_extracted["saved_fields"] = sorted(saved_set)
        current_extracted["last_saved"] = saved_keys[-1]

    # Update chat row
    admin.table("brand_chats").update({
        "messages": messages,
        "extracted": current_extracted,
    }).eq("id", chat_row["id"]).execute()

    return StrategistChatResponse(
        responses=parsed_responses,
        completeness=completeness,
        chat_id=chat_row["id"],
    )


# -- GET /brand/strategist/completeness/{brand_id} --------------------


@router.get("/completeness/{brand_id}", response_model=FieldCompletenessResponse)
async def get_completeness(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get field-level completeness for a brand."""
    admin = get_admin_client()
    brand_row = _get_brand_row(admin, brand_id, user.id)
    profile_json = brand_row.get("profile_json") or {}

    completeness = calculate_field_completeness(profile_json)

    return FieldCompletenessResponse(
        overall_percent=completeness["overall_percent"],
        overall_filled=completeness["overall_filled"],
        overall_total=completeness["overall_total"],
        modules=completeness["modules"],
        filled_fields=completeness["filled_fields"],
        unfilled_fields=completeness["unfilled_fields"],
    )


# -- GET /brand/strategist/next-field/{brand_id} -----------------------


@router.get("/next-field/{brand_id}", response_model=NextFieldResponse)
async def get_next_field_endpoint(
    brand_id: str,
    context: Optional[str] = Query(None, description="Recent user message for context scoring"),
    user: CurrentUser = Depends(get_current_user),
):
    """Get the next recommended field to ask about."""
    admin = get_admin_client()
    brand_row = _get_brand_row(admin, brand_id, user.id)
    profile_json = brand_row.get("profile_json") or {}

    next_f = get_next_field(profile_json, context_hint=context)

    if not next_f:
        return NextFieldResponse(all_complete=True)

    return NextFieldResponse(
        module=next_f.module,
        field=next_f.key,
        label=next_f.label,
        question=next_f.question,
    )


# -- POST /brand/strategist/save-field ---------------------------------


@router.post("/save-field")
async def save_field_endpoint(
    brand_id: str = Query(..., description="Personal brand ID"),
    module: str = Query(..., description="Module name"),
    field: str = Query(..., description="Field key"),
    user: CurrentUser = Depends(get_current_user),
    body: Dict[str, Any] = ...,
):
    """Explicitly save a field value to the brand profile."""
    admin = get_admin_client()
    brand_row = _get_brand_row(admin, brand_id, user.id)
    profile_json = brand_row.get("profile_json") or {}

    value = body.get("value")
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'value' in request body",
        )

    full_key = f"{module}.{field}"
    field_def = get_field(full_key)
    if not field_def:
        logger.warning("Saving unknown field %s", full_key)

    updated = save_field_to_profile(profile_json, module, field, value)

    admin.table("personal_brands").update({
        "profile_json": updated,
    }).eq("id", brand_id).execute()

    completeness = calculate_field_completeness(updated)

    return {
        "saved": full_key,
        "completeness": completeness,
    }


# -- POST /brand/strategist/chat/{brand_id}/resume --------------------


@router.post("/chat/{brand_id}/resume")
async def resume_strategist_chat(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Resume an existing strategist chat session.

    Returns full conversation history so the frontend can reconstruct
    all previous turns (user messages + assistant responses).
    """
    admin = get_admin_client()
    brand_row = _get_brand_row(admin, brand_id, user.id)
    profile_json = brand_row.get("profile_json") or {}

    chat_row = _get_or_create_strategist_chat(
        admin, user.id, brand_id, profile_json,
    )

    messages = chat_row.get("messages", []) or []
    parsed = _parse_last_assistant_responses(messages)
    completeness = calculate_field_completeness(profile_json)

    return StrategistChatResponse(
        responses=parsed,
        completeness=completeness,
        chat_id=chat_row["id"],
        history=messages,
    )


# -- POST /brand/strategist/chat/{brand_id}/new -----------------------


@router.post("/chat/{brand_id}/new")
async def start_new_strategist_chat(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Start a fresh strategist chat session."""
    admin = get_admin_client()
    brand_row = _get_brand_row(admin, brand_id, user.id)
    profile_json = brand_row.get("profile_json") or {}

    # Deactivate existing strategist chats
    admin.table("brand_chats").update({
        "status": "completed",
    }).eq("user_id", user.id).eq("brand_id", brand_id).eq(
        "module", "strategist",
    ).eq("status", "active").execute()

    chat_row = _get_or_create_strategist_chat(
        admin, user.id, brand_id, profile_json,
    )

    messages = chat_row.get("messages", []) or []
    parsed = _parse_last_assistant_responses(messages)
    completeness = calculate_field_completeness(profile_json)

    return StrategistChatResponse(
        responses=parsed,
        completeness=completeness,
        chat_id=chat_row["id"],
        history=messages,
    )


# -- GET /brand/strategist/chat/history (backward compat) --------------


@router.get("/chat/history")
async def get_strategist_chat_history(
    brand_id: str = Query(..., description="Personal brand ID"),
    user: CurrentUser = Depends(get_current_user),
):
    """Get the raw strategist chat history for a brand."""
    admin = get_admin_client()
    brand_row = _get_brand_row(admin, brand_id, user.id)
    profile_json = brand_row.get("profile_json") or {}

    chat_row = _get_or_create_strategist_chat(
        admin, user.id, brand_id, profile_json,
    )

    return {
        "chat_id": chat_row["id"],
        "messages": chat_row.get("messages", []),
        "extracted": chat_row.get("extracted", {}),
        "status": chat_row.get("status", "active"),
    }
