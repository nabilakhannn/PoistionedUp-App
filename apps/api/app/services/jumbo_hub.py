"""Jumbo Hub Service — Slice 107.

Persistent multi-turn chat with Jumbo (general-purpose AI partner).
Conversations are per-brand and stored in jumbo_conversations table.

Also provides save-as-note to persist Jumbo responses to agent_memory.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger("app.services.jumbo_hub")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

MAX_MESSAGES_PER_CONVERSATION = 100
MAX_MESSAGE_LENGTH = 5000
MAX_TITLE_LENGTH = 60

_JUMBO_HUB_SYSTEM = """\
You are Jumbo, a world-class business strategist and AI partner for PositionedUp.

You think like the top businessman in the world. When asked about offers, \
you apply the Hormozi Value Equation and Grand Slam framework. When asked about \
funnels, you architect complete systems (traffic -> opt-in -> nurture -> close). \
When asked about content, you use the Messaging Buckets framework (Pain, Outcome, \
Story, Authority, Belief, Curiosity) and the TOFU/MOFU/BOFU funnel.

You help with ANYTHING: content strategy, offer design, pricing, positioning, \
funnel architecture, sales scripts, competitive positioning, growth strategy. \
You are not limited to content planning.

You have this brand's full dossier pre-loaded. Reference it when relevant, \
but don't force it into every answer.

Style: Smart colleague energy. Direct, no filler, no corporate speak. \
When you write content, use the brand voice. When advising, be candid and specific. \
Give frameworks and next steps, not vague advice.

BRAND DOSSIER:
{dossier_json}
"""


def _get_brand_dossier(brand_id: str) -> str:
    """Load brand context for system prompt injection."""
    try:
        from app.services.jumbo_pipeline import get_brand_context
        ctx = get_brand_context(brand_id)
        if ctx:
            return json.dumps(ctx, default=str, indent=2)
    except Exception as exc:
        logger.warning("Failed to load brand context for hub: %s", exc)
    return '{"note": "Brand context unavailable — answer based on general knowledge."}'


def _format_history(messages: list, limit: int = 20) -> str:
    """Format recent messages for LLM context."""
    recent = messages[-limit:] if len(messages) > limit else messages
    lines = []
    for msg in recent:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def _auto_title(message: str) -> str:
    """Generate conversation title from first user message."""
    clean = re.sub(r"\s+", " ", message).strip()
    if len(clean) <= MAX_TITLE_LENGTH:
        return clean
    return clean[:MAX_TITLE_LENGTH - 3] + "..."


def _strip_control_chars(text: str) -> str:
    """Remove control characters except newlines and tabs."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


# ── Conversation CRUD ────────────────────────────────────────────────────


def create_conversation(user_id: str, brand_id: str) -> dict:
    """Create a new conversation. Returns {id, title, brand_id, messages}."""
    from app.deps import get_admin_client
    sb = get_admin_client()

    result = (
        sb.table("jumbo_conversations")
        .insert({
            "user_id": user_id,
            "brand_id": brand_id,
            "title": "New Chat",
            "messages": json.dumps([]),
            "status": "active",
        })
        .execute()
    )

    if not result.data:
        raise RuntimeError("Failed to create conversation")

    row = result.data[0]
    return {
        "id": row["id"],
        "title": row["title"],
        "brand_id": row["brand_id"],
        "messages": [],
        "created_at": row["created_at"],
    }


def chat(user_id: str, conversation_id: str, message: str) -> dict:
    """Send a message and get Jumbo's response.

    Returns {response, conversation_id, title}.
    Raises ValueError on validation errors.
    """
    from app.deps import get_admin_client
    from app.services.tool_use_agents import run_tool_use_agent

    message = _strip_control_chars(message.strip())
    if not message:
        raise ValueError("Message cannot be empty")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message exceeds {MAX_MESSAGE_LENGTH} character limit")

    sb = get_admin_client()

    # Fetch conversation with IDOR check
    conv_result = (
        sb.table("jumbo_conversations")
        .select("*")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not conv_result.data:
        raise LookupError("Conversation not found")

    conv = conv_result.data[0]
    messages: list = conv.get("messages") or []

    if isinstance(messages, str):
        messages = json.loads(messages)

    if len(messages) >= MAX_MESSAGES_PER_CONVERSATION:
        raise ValueError(
            f"Conversation has reached the {MAX_MESSAGES_PER_CONVERSATION} message limit. "
            "Please start a new conversation."
        )

    # Append user message
    now_iso = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": message, "created_at": now_iso}
    messages.append(user_msg)

    # Build system prompt with brand dossier
    brand_id = conv["brand_id"]
    dossier = _get_brand_dossier(brand_id)
    system_prompt = _JUMBO_HUB_SYSTEM.format(dossier_json=dossier)

    # Build user prompt with conversation history
    history = _format_history(messages)
    user_prompt = (
        "Continue this conversation. Respond only as Jumbo.\n\n"
        f"CONVERSATION:\n{history}"
    )

    # Call LLM
    result = run_tool_use_agent(
        agent_id="jumbo",
        task_type="hub_chat",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        user_id=user_id,
        brand_id=brand_id,
        available_tools=["web_search", "read_playbook"],
    )

    response_text = result.content if result.success else (
        "I'm having trouble right now. Try sending your message again."
    )

    # Append Jumbo response
    jumbo_msg = {"role": "jumbo", "content": response_text, "created_at": datetime.now(timezone.utc).isoformat()}
    messages.append(jumbo_msg)

    # Auto-title from first user message if still default
    title = conv["title"]
    if title == "New Chat":
        first_user = next((m for m in messages if m.get("role") == "user"), None)
        if first_user:
            title = _auto_title(first_user["content"])

    # Persist
    sb.table("jumbo_conversations").update({
        "messages": json.dumps(messages, default=str),
        "title": title,
    }).eq("id", conversation_id).execute()

    return {
        "response": response_text,
        "conversation_id": conversation_id,
        "title": title,
    }


def list_conversations(
    user_id: str, brand_id: str, limit: int = 20
) -> List[dict]:
    """List active conversations for a brand, most recent first."""
    from app.deps import get_admin_client
    sb = get_admin_client()

    result = (
        sb.table("jumbo_conversations")
        .select("id, title, brand_id, status, created_at, updated_at")
        .eq("user_id", user_id)
        .eq("brand_id", brand_id)
        .eq("status", "active")
        .order("updated_at", desc=True)
        .limit(min(limit, 50))
        .execute()
    )

    return result.data or []


def get_conversation(user_id: str, conversation_id: str) -> Optional[dict]:
    """Get a full conversation with messages. Returns None if not found / IDOR."""
    from app.deps import get_admin_client
    sb = get_admin_client()

    result = (
        sb.table("jumbo_conversations")
        .select("*")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    row = result.data[0]
    messages = row.get("messages") or []
    if isinstance(messages, str):
        messages = json.loads(messages)
    row["messages"] = messages
    return row


def archive_conversation(user_id: str, conversation_id: str) -> bool:
    """Archive a conversation. Returns True if updated, False if not found."""
    from app.deps import get_admin_client
    sb = get_admin_client()

    result = (
        sb.table("jumbo_conversations")
        .update({"status": "archived"})
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )

    return bool(result.data)


def save_as_note(
    user_id: str, brand_id: str, content: str, title: str = ""
) -> Optional[str]:
    """Save text as agent_memory entry. Returns memory ID or None."""
    from app.deps import get_admin_client
    sb = get_admin_client()

    content = _strip_control_chars(content.strip())
    title = _strip_control_chars((title or "Jumbo note").strip())[:200]

    if not content:
        return None

    try:
        result = (
            sb.table("agent_memory")
            .insert({
                "user_id": user_id,
                "brand_id": brand_id,
                "memory_type": "user_note",
                "content": content[:10000],
                "source": "jumbo_hub",
                "title": title,
            })
            .execute()
        )
        if result.data:
            return result.data[0].get("id")
    except Exception as exc:
        logger.warning("save_as_note failed: %s", exc)

    return None
