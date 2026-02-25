"""Brand Strategist v2 service -- Agentic coaching engine.

The strategist is NOT a form processor. It's a coaching AI that:
- Remembers everything said in the conversation
- References earlier answers when asking new questions
- Pushes back on vague answers
- Connects dots across modules
- Flows naturally from one topic to the next
- Can have free-form discussions when the user wants to talk

KEY ARCHITECTURAL DECISION (Slice 63):
The LLM sees a NATURAL conversation history (plain text), not raw JSON.
Before sending to the LLM, we transform JSON assistant messages into
readable coaching text. The LLM responds naturally, and we parse its
output back into structured JSON for the frontend.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

from app.services.brand_fields import (
    ALL_FIELDS,
    BrandField,
    FIELDS_BY_KEY,
    FIELDS_BY_MODULE,
    MODULE_LABELS,
    MODULES,
    TOTAL_FIELDS,
    get_field,
    get_module_fields,
)
from app.services.brand_sequencing import (
    calculate_field_completeness,
    get_filled_fields,
    get_next_field,
    get_resume_message,
    get_transition_message,
)

logger = logging.getLogger("app.services.brand_strategist")

# In-memory cache for DB-stored prompt configs
_prompt_config_cache: Dict[str, str] = {}


def _get_trainable_config(config_key: str, fallback: str) -> str:
    """Get a prompt configuration from DB cache or return fallback."""
    if config_key in _prompt_config_cache:
        return _prompt_config_cache[config_key]
    return fallback


def load_prompt_configs_from_db() -> None:
    """Load all agent prompt configs into memory cache."""
    try:
        from app.deps import get_admin_client
        admin = get_admin_client()
        resp = (
            admin.table("agent_training_config")
            .select("config_key, content")
            .eq("is_active", True)
            .execute()
        )
        if resp.data:
            for row in resp.data:
                _prompt_config_cache[row["config_key"]] = row["content"]
            logger.info("Loaded %d prompt configs from DB", len(resp.data))
    except Exception:
        logger.debug("Could not load prompt configs from DB")


def clear_prompt_config_cache() -> None:
    """Clear the prompt config cache."""
    _prompt_config_cache.clear()


# ── System Prompt (v2 -- Slim, agentic) ──────────────────────────

STRATEGIST_SYSTEM = """\
You are PositionedUp, a $100K personal brand strategist compressed into AI.

You coach like Alex Hormozi meets a world-class brand consultant. Direct, \
specific, no fluff. You have a BRAIN: you remember what the user said, \
connect dots between their answers, push back on vagueness, and have opinions.

HOW YOU OPERATE:
- You are building the user's Brand DNA across 8 modules (Foundation, \
Authority, ICA, Positioning, Voice, Offer, Content Pillars, Competitive).
- Each module has fields to fill. You ask coaching questions to fill them.
- When you have enough from the user's answer, SAVE the field and \
IMMEDIATELY ask the next question in the same response. Never stop.
- When the user wants to discuss, tweak, or push back, engage naturally. \
You are a coach with opinions, not a form.
- Reference their earlier answers when asking new questions.
- If an answer is vague or generic, challenge it. Ask for specifics.

RESPONSE FORMAT:
You must respond with a JSON object: {"responses": [...]}
The array contains one or more response objects of these types:

1. SAVE + NEXT QUESTION (most common after user answers):
{"responses": [
  {"type": "save", "module": "foundation", "field": "what_you_do", \
"value": "I help B2B SaaS founders scale revenue", \
"message": "Solid. Revenue scaling for SaaS founders gives me a lot to work with."},
  {"type": "options", "module": "foundation", "field": "current_clients", \
"message": "Who is paying you right now? If nobody yet, who do you want?", \
"options": [
    {"id": "A", "label": "Early-stage founders", "text": "Pre-revenue SaaS founders..."},
    {"id": "B", "label": "Growth-stage teams", "text": "SaaS companies doing $1-5M ARR..."}
  ], "allow_custom": true, "allow_skip": true}
]}

2. QUESTION WITH OPTIONS (when asking a new field):
{"responses": [
  {"type": "options", "module": "ica", "field": "pain_points", \
"message": "Your coaching question that references what you know about them", \
"options": [{"id": "A", "label": "...", "text": "..."}, \
{"id": "B", "label": "...", "text": "..."}], \
"allow_custom": true, "allow_skip": true}
]}

3. COACHING MESSAGE (when discussing, pushing back, or having a conversation):
{"responses": [
  {"type": "message", "message": "Your multi-paragraph coaching response."}
]}

4. REFINEMENT (polishing user's answer before saving):
{"responses": [
  {"type": "refinement", "module": "foundation", "field": "what_you_do", \
"message": "Let me sharpen that for you.", \
"refined_text": "Polished version of their answer", \
"actions": ["confirm", "edit"]}
]}

RULES:
- Options must be specific to THIS user. Reference their earlier answers.
- Each option is a genuinely different strategic direction (2-3 max).
- After saving, ALWAYS include the next question. NEVER return just a save alone.
- Never output percentages, "saved successfully", or progress metrics. The frontend handles that.
- When the user asks "what do you think" or wants to discuss, use type "message" and engage.
- Module and field values must match the field names exactly.
- Keep your coaching messages punchy. Short paragraphs. Direct language.
"""

# ── Human Writing Rules (appended to system prompt) ──────────────
# Imported from writing_style.py, appended in build_strategist_system_prompt()


# ── Build System Prompt ──────────────────────────────────────────


def build_strategist_system_prompt(
    profile_json: Dict[str, Any],
    next_field: Optional[BrandField] = None,
    completeness: Optional[Dict[str, Any]] = None,
    filled_fields: Optional[Set[str]] = None,
    resource_context: str = "",
    performance_context: str = "",
    memory_context: str = "",
    research_context: str = "",
    training_context: str = "",
    user_id: Optional[str] = None,
    brand_id: Optional[str] = None,
) -> str:
    """Build the full system prompt for the strategist.

    Much slimmer than v1. Core identity + format rules + context.
    The conversation history provides most of the coaching context.
    """
    parts = []

    # Core identity (DB-configurable or hardcoded fallback)
    identity = _get_trainable_config("strategist_identity", STRATEGIST_SYSTEM)
    parts.append(identity)

    # Already answered fields + their values (compact)
    profile_summary = _build_profile_context(profile_json)
    if profile_summary:
        parts.append(profile_summary)

    # What to ask next
    if next_field:
        parts.append(
            f"NEXT FIELD TO ASK:\n"
            f"Module: {next_field.module} | Field: {next_field.key}\n"
            f"Question: {next_field.question}\n"
            f"Generate 2-3 personalized options based on what you know about this user."
        )
    elif completeness and completeness.get("overall_percent", 0) >= 100:
        parts.append(
            "ALL FIELDS COMPLETE. The user's Brand DNA is fully built. "
            "Now help them with content strategy, refinement, or anything they want."
        )

    # Document handling
    parts.append(
        "DOCUMENTS: When the user provides document text (files, links), "
        "read it, reference specific details, and use it in your coaching."
    )

    # Writing style
    parts.append(HUMAN_WRITING_RULES)

    # Optional context layers (keep them compact)
    if resource_context:
        parts.append("--- USER'S KNOWLEDGE ---\n" + resource_context[:2000])
    if performance_context:
        parts.append(performance_context[:1000])
    if memory_context:
        parts.append(memory_context[:1000])
    if research_context:
        parts.append(research_context[:1000])

    # Training context
    if training_context:
        parts.append("--- TRAINING ---\n" + training_context)
    elif user_id:
        try:
            from app.services.agent_training import (
                build_training_context as _build_ctx,
            )
            cur_module = next_field.module if next_field else None
            cur_field = next_field.key if next_field else None
            auto_ctx = _build_ctx(
                user_id=user_id, brand_id=brand_id,
                current_module=cur_module, current_field=cur_field,
            )
            if auto_ctx:
                parts.append(auto_ctx)
        except Exception:
            pass

    return "\n\n".join(parts)


def _build_profile_context(profile_json: Dict[str, Any]) -> str:
    """Build a compact, readable summary of what the user has told us.

    This is CRITICAL for the model to reference earlier answers and
    connect dots. Format: conversational summary, not field dumps.
    """
    if not profile_json:
        return ""

    lines = []
    filled_count = 0

    for module in MODULES:
        module_data = profile_json.get(module, {})
        if not isinstance(module_data, dict):
            continue

        module_entries = []
        for key, value in module_data.items():
            if value is None or value == "" or value == [] or value == {}:
                continue
            filled_count += 1

            # Make values readable
            if isinstance(value, str):
                display = value[:150] + "..." if len(value) > 150 else value
            elif isinstance(value, list):
                display = ", ".join(str(v) for v in value[:5])
            elif isinstance(value, dict):
                display = json.dumps(value, default=str)[:150]
            else:
                display = str(value)

            label = MODULE_LABELS.get(module, module)
            field_def = get_field(f"{module}.{key}")
            field_label = field_def.label if field_def else key.replace("_", " ").title()
            module_entries.append(f"  {field_label}: {display}")

        if module_entries:
            label = MODULE_LABELS.get(module, module)
            lines.append(f"[{label}]")
            lines.extend(module_entries)

    if not lines:
        return ""

    return (
        f"WHAT THE USER HAS TOLD YOU SO FAR ({filled_count} fields filled):\n"
        "Reference these naturally in your coaching. Connect dots.\n\n"
        + "\n".join(lines)
    )


# ── Conversation History Transformer ─────────────────────────────


def transform_history_for_llm(
    messages: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Transform raw conversation history into natural text for the LLM.

    Problem: Assistant messages are stored as raw JSON like:
    {"responses": [{"type": "save", ...}, {"type": "options", ...}]}

    The LLM cannot maintain a coaching voice when it sees JSON dumps
    as its own conversation history. This function extracts the human-
    readable coaching text from each assistant message.

    User messages pass through unchanged.
    """
    transformed = []

    for msg in messages:
        role = msg.get("role", "")

        if role == "user":
            # User messages pass through, but strip metadata prefixes
            content = msg.get("content", "")
            # Remove [USER_ACTION: ...] and [TARGET_FIELD: ...] metadata
            content = re.sub(r"\[USER_ACTION:[^\]]+\]\s*", "", content)
            content = re.sub(r"\[TARGET_FIELD:[^\]]+\]\s*", "", content)
            transformed.append({"role": "user", "content": content.strip()})

        elif role == "assistant":
            # Extract coaching text from JSON responses
            content = msg.get("content", "")
            natural_text = _json_to_coaching_text(content)
            if natural_text:
                transformed.append({"role": "assistant", "content": natural_text})

        elif role == "system":
            # System messages pass through (shouldn't be in conversation)
            transformed.append(msg)

    return transformed


def _json_to_coaching_text(raw_content: str) -> str:
    """Convert a JSON assistant response into natural coaching text.

    Extracts the 'message' fields from structured responses and
    combines them into readable coaching text. This way the LLM
    sees its past responses as natural language, not JSON.
    """
    text = raw_content.strip()

    # Try to parse as JSON
    try:
        # Strip code fences
        if text.startswith("```"):
            first_nl = text.find("\n")
            if first_nl > 0:
                text = text[first_nl + 1:]
            if text.endswith("```"):
                text = text[:-3].strip()

        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        # Not JSON, return as-is (already natural text)
        return raw_content.strip()

    # Extract response items
    items = []
    if isinstance(data, dict) and "responses" in data:
        items = data["responses"]
    elif isinstance(data, dict) and "type" in data:
        items = [data]
    elif isinstance(data, list):
        items = data

    if not items:
        return raw_content.strip()

    # Build natural text from each response item
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue

        resp_type = item.get("type", "")
        message = item.get("message", "")

        if resp_type == "save":
            # Brief save acknowledgment (the coaching comment)
            if message:
                parts.append(message)

        elif resp_type == "options":
            # The coaching question + options as readable text
            if message:
                parts.append(message)
            options = item.get("options", [])
            if options:
                for opt in options:
                    if isinstance(opt, dict):
                        opt_id = opt.get("id", "")
                        label = opt.get("label", "")
                        opt_text = opt.get("text", "")
                        parts.append(f"  {opt_id}) {label}: {opt_text}")

        elif resp_type == "refinement":
            if message:
                parts.append(message)
            refined = item.get("refined_text", "")
            if refined:
                parts.append(f'Refined version: "{refined}"')

        elif resp_type == "message":
            if message:
                parts.append(message)

        elif resp_type == "content":
            if message:
                parts.append(message)

    return "\n\n".join(parts) if parts else raw_content.strip()


# ── Welcome & Resume Messages ──────────────────────────────────


def get_welcome_message() -> Dict[str, Any]:
    """Generate the welcome message for a first-time user."""
    return {
        "type": "message",
        "message": (
            "I am your personal brand strategist. Think of me as the "
            "consultant who charges $100K but you got me for free.\n\n"
            "Before I can build anything for you, I need to understand "
            "who you are and what you are working with. The better your "
            "answers, the sharper everything I create will be.\n\n"
            "Let us start."
        ),
    }


def get_welcome_with_first_question(
    first_field: Optional[BrandField] = None,
) -> List[Dict[str, Any]]:
    """Generate welcome message followed by the first question."""
    responses = [get_welcome_message()]

    field = first_field or get_field("foundation.what_you_do")

    if field:
        responses.append({
            "type": "options",
            "module": field.module,
            "field": field.key,
            "message": field.question,
            "options": [],  # No options for first question (zero context)
            "allow_custom": True,
            "allow_skip": False,
        })

    return responses


def build_resume_responses(
    profile_json: Dict[str, Any],
    next_field: Optional[BrandField] = None,
) -> List[Dict[str, Any]]:
    """Generate resume messages for a returning user."""
    completeness = calculate_field_completeness(profile_json)
    resume_msg = get_resume_message(completeness)

    responses = []

    if resume_msg:
        responses.append({"type": "message", "message": resume_msg})

    if next_field:
        responses.append({
            "type": "options",
            "module": next_field.module,
            "field": next_field.key,
            "message": next_field.question,
            "options": [],
            "allow_custom": True,
            "allow_skip": True,
        })

    return responses


# ── Response Parsing (robust: handles text + JSON) ───────────────


def parse_strategist_response(content: str) -> List[Dict[str, Any]]:
    """Parse the LLM response into structured response objects.

    Handles multiple formats:
    1. Clean JSON: {"responses": [...]}
    2. Single JSON object: {"type": "options", ...}
    3. JSON array: [{"type": "save", ...}, ...]
    4. Mixed text + JSON: Coaching text followed by a JSON block
    5. Plain text fallback: Wraps in a message response

    The parser is intentionally permissive because removing
    response_format=json_object means the LLM might include
    reasoning text before/after the JSON.
    """
    text = content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl > 0:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()

    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(text)
        return _extract_responses_from_json(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    # Strategy 2: Find JSON block in mixed text+JSON
    # The LLM might output: "Let me think about this...\n\n{\"responses\": [...]}"
    json_match = _find_json_block(text)
    if json_match:
        try:
            data = json.loads(json_match)
            return _extract_responses_from_json(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Strategy 3: The LLM responded in plain text (coaching message)
    # This is valid when the model is having a conversation
    logger.info("Strategist responded in plain text (wrapping as message)")
    return [{"type": "message", "message": content.strip()}]


def _extract_responses_from_json(data: Any) -> List[Dict[str, Any]]:
    """Extract response items from parsed JSON data."""
    # Wrapper format: {"responses": [...]}
    if isinstance(data, dict) and "responses" in data:
        items = data["responses"]
        if isinstance(items, list):
            valid = [i for i in items if isinstance(i, dict) and "type" in i]
            if valid:
                return valid

    # Single response object
    if isinstance(data, dict) and "type" in data:
        return [data]

    # Legacy format: {reply, extracted}
    if isinstance(data, dict) and "reply" in data:
        return _convert_legacy_response(data)

    # Array of response objects
    if isinstance(data, list):
        valid = []
        for item in data:
            if isinstance(item, dict) and "type" in item:
                valid.append(item)
            elif isinstance(item, dict) and "reply" in item:
                valid.extend(_convert_legacy_response(item))
        if valid:
            return valid

    # Unknown JSON structure, wrap as message
    if isinstance(data, dict):
        msg = data.get("message", "") or json.dumps(data)
        return [{"type": "message", "message": msg}]

    return [{"type": "message", "message": str(data)}]


def _find_json_block(text: str) -> Optional[str]:
    """Find the largest valid-looking JSON block in mixed text.

    Scans for { or [ characters and tries to find matching closers.
    Returns the extracted JSON string or None.
    """
    # Try to find {"responses": ...} or [...]
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue
        # Find the matching closing bracket from the end
        end_idx = text.rfind(end_char)
        if end_idx > start_idx:
            candidate = text[start_idx:end_idx + 1]
            # Quick validation: try to parse
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

    return None


def _convert_legacy_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert a legacy {reply, extracted} response to the new format."""
    responses = []
    reply = data.get("reply", "")
    extracted = data.get("extracted", {})

    if reply:
        responses.append({"type": "message", "message": reply})

    if extracted:
        for key, value in extracted.items():
            if value is not None and value != "" and value != [] and value != {}:
                if "." in key:
                    module, field = key.split(".", 1)
                else:
                    module = "unknown"
                    field = key
                responses.append({
                    "type": "save", "module": module, "field": field,
                    "value": value, "message": "",
                })

    return responses if responses else [{"type": "message", "message": ""}]


# ── Field Save Logic ────────────────────────────────────────────


def save_field_to_profile(
    profile_json: Dict[str, Any],
    module: str,
    field: str,
    value: Any,
) -> Dict[str, Any]:
    """Save a confirmed field value to the profile_json."""
    if not profile_json:
        profile_json = {}
    if module not in profile_json:
        profile_json[module] = {}
    if not isinstance(profile_json[module], dict):
        profile_json[module] = {}
    profile_json[module][field] = value
    logger.info("Saved field %s.%s to profile", module, field)
    return profile_json


def save_fields_from_responses(
    profile_json: Dict[str, Any],
    responses: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[str]]:
    """Process responses and save any 'save' type fields.

    Returns (updated_profile_json, list_of_saved_field_keys).
    """
    saved_keys = []
    updated = dict(profile_json) if profile_json else {}

    for response in responses:
        if response.get("type") == "save":
            module = response.get("module", "")
            field = response.get("field", "")
            value = response.get("value")

            if module and field and value is not None:
                full_key = f"{module}.{field}"
                updated = save_field_to_profile(updated, module, field, value)
                saved_keys.append(full_key)

    return updated, saved_keys


# ── Context Fetchers ────────────────────────────────────────────


def fetch_all_context(
    user_id: str,
    user_message: str,
    profile_json: Dict[str, Any],
    brand_id: Optional[str] = None,
) -> Dict[str, str]:
    """Fetch all context layers for the strategist prompt."""
    from app.services.brand_chat import (
        get_relevant_context,
        _fetch_memory_context,
        _fetch_performance_context,
        _fetch_research_context,
    )

    return {
        "resource": get_relevant_context(user_message, user_id, brand_id),
        "performance": _fetch_performance_context(user_id, brand_id),
        "memory": _fetch_memory_context(user_id, brand_id),
        "research": _fetch_research_context(user_message, profile_json),
    }


# ── Chat Message Builder ───────────────────────────────────────


def build_strategist_messages(
    profile_json: Dict[str, Any],
    conversation: List[Dict[str, str]],
    next_field: Optional[BrandField] = None,
    resource_context: str = "",
    performance_context: str = "",
    memory_context: str = "",
    research_context: str = "",
    document_context: str = "",
    training_context: str = "",
    user_id: Optional[str] = None,
    brand_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Build the LLM messages array for the strategist.

    KEY CHANGE (Slice 63): Conversation history is TRANSFORMED from
    raw JSON into natural coaching text before sending to the LLM.
    This lets the model maintain a conversational coaching voice
    instead of outputting mechanical JSON.
    """
    filled = get_filled_fields(profile_json)
    completeness = calculate_field_completeness(profile_json)

    system = build_strategist_system_prompt(
        profile_json=profile_json,
        next_field=next_field,
        completeness=completeness,
        filled_fields=filled,
        resource_context=resource_context,
        performance_context=performance_context,
        memory_context=memory_context,
        research_context=research_context,
        training_context=training_context,
        user_id=user_id,
        brand_id=brand_id,
    )

    messages = [{"role": "system", "content": system}]

    # Inject document context as a dedicated user message
    if document_context:
        messages.append({
            "role": "user",
            "content": (
                "DOCUMENT_CONTEXT (extracted text from user's upload):\n\n"
                + document_context
            ),
        })
        messages.append({
            "role": "assistant",
            "content": "Got it, I have the document. Let me review it.",
        })

    # Transform conversation history: JSON -> natural coaching text
    natural_conversation = transform_history_for_llm(conversation)
    messages.extend(natural_conversation)

    return messages


# ── Pushback Templates ──────────────────────────────────────────

PUSHBACK_TEMPLATES = {
    "vague_what_you_do": (
        "That could mean anything. What SPECIFIC transformation do you "
        "deliver? What does someone's situation look like BEFORE they work "
        "with you, and what does it look like AFTER?"
    ),
    "vague_goal": (
        "Visibility is not a goal, it is a means to a goal. What do you "
        "want the visibility to DO for you? How many clients? What revenue?"
    ),
    "vague_tried_everything": (
        "List three specific things you tried and tell me why each one failed."
    ),
    "skip_brand_for_content": (
        "I could write you a generic post right now, but it would sound like "
        "every other generic post online. Give me 10 minutes of your time to "
        "understand your brand, and I will write you something that actually "
        "sounds like you and attracts your ideal clients. Deal?"
    ),
    "no_time": (
        "I hear you. Here is the minimum viable version: answer 5 questions, "
        "I build your brand DNA in 15 minutes, and I give you your first "
        "week of content ready to post. Can you give me 15 minutes right now?"
    ),
    "no_results": (
        "Everyone starts at zero. We lean on YOUR story. Your journey. Your "
        "transformation. Your mistakes and lessons. That IS proof. People do "
        "not buy from people with the most credentials. They buy from people "
        "who understand their situation."
    ),
    "copy_someone": (
        "No. Copying someone else's brand makes you a second-rate version of "
        "them. I will study what works for them and reverse-engineer the "
        "PRINCIPLES, then apply those principles to YOUR unique angle."
    ),
}
