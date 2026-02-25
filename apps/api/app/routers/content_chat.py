"""Content Chat router -- manual mode content creation via AI chat.

Users configure their content settings (objective, format, tone, length,
pillars, platform) and then chat with the AI to research and write content
iteratively. This is the manual complement to the 8-node automation pipeline.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import get_current_user, CurrentUser
from app.deps import get_admin_client
from worker.graph.llm import get_llm_client
from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES, AI_TELLS_CHECKLIST

logger = logging.getLogger("app.routers.content_chat")

router = APIRouter(prefix="/content-chat", tags=["content-chat"])


# ── Schemas ──────────────────────────────────────────────

class ContentChatMessage(BaseModel):
    """A single message in the content chat."""
    role: str
    content: str


class ContentChatRequest(BaseModel):
    """Request body for sending a message in the content chat."""
    message: str = Field(..., min_length=1, max_length=5000)
    chat_id: Optional[str] = None
    brand_id: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


class ContentChatResponse(BaseModel):
    """Response from the content chat."""
    reply: str
    chat_id: str
    messages: List[ContentChatMessage]


class ContentChatHistory(BaseModel):
    """Full chat history."""
    chat_id: str
    messages: List[ContentChatMessage]
    settings: Dict[str, Any]
    created_at: str


class ContentChatListItem(BaseModel):
    """Summary of a content chat for listing."""
    chat_id: str
    title: Optional[str] = None
    preview: str
    settings: Dict[str, Any]
    created_at: str
    message_count: int


# ── System prompt ────────────────────────────────────────

CONTENT_CHAT_SYSTEM = """You are a content strategist and writer working inside a Content Studio. \
The user chats with you on the left, and your content drafts appear on a Canvas on the right.

Your role:
- Research topics, develop angles, and find data points when asked
- Write full content drafts (scripts, posts, threads) in the creator's voice
- Offer multiple hook or angle options when brainstorming
- Be specific and actionable, never generic or vague
- Ask clarifying questions only when truly needed

You have access to the creator's brand profile and content settings below. \
Use these to guide your writing style, tone, and content direction.

CRITICAL FORMATTING RULES (the Canvas parses your markdown):
- ALWAYS use ## headers to separate content sections (Hook, Intro, Body, CTA, etc.)
- When writing scripts, structure with clear ## section headers
- When suggesting hooks, use ## Hooks as a header and number each hook
- When writing LinkedIn posts, use ## Post 1, ## Post 2, etc.
- When writing Twitter threads, use ## Tweet 1, ## Tweet 2, etc.
- Use **bold** for emphasis and key phrases
- Use numbered lists for options and steps
- Keep each section focused and self-contained so the user can edit them individually

Example script structure:
## Hook
(attention-grabbing opening)

## Introduction
(context and why this matters)

## Main Points
(the core content)

## Call to Action
(what the viewer should do next)

Always respond in plain text with markdown formatting (not JSON).
""" + HUMAN_WRITING_RULES + "\n\n" + AI_TELLS_CHECKLIST


def _build_system_message(
    settings: Dict[str, Any],
    profile_snapshot: Dict[str, Any],
) -> str:
    """Build the full system message with content settings and brand context."""
    parts = [CONTENT_CHAT_SYSTEM]

    # Content settings
    setting_lines = []
    if settings.get("objective"):
        setting_lines.append(f"Content Objective: {settings['objective']}")
    if settings.get("content_type"):
        setting_lines.append(f"Content Style: {settings['content_type']}")
    if settings.get("platforms"):
        setting_lines.append(f"Target Platforms: {', '.join(settings['platforms'])}")
    if settings.get("tone"):
        setting_lines.append(f"Tone: {settings['tone']}")
    if settings.get("content_length"):
        setting_lines.append(f"Content Length: {settings['content_length']}")
    if settings.get("content_pillars"):
        setting_lines.append(f"Content Pillars: {', '.join(settings['content_pillars'])}")

    if setting_lines:
        parts.append("\n## Content Settings\n" + "\n".join(setting_lines))

    # Brand context
    if profile_snapshot:
        brand_parts = []
        if profile_snapshot.get("foundation"):
            f = profile_snapshot["foundation"]
            if f.get("beliefs"):
                brand_parts.append(f"Core Beliefs: {', '.join(f['beliefs'][:5])}")
            if f.get("content_pillars"):
                brand_parts.append(f"Brand Pillars: {', '.join(f['content_pillars'])}")
        if profile_snapshot.get("ica"):
            ica = profile_snapshot["ica"]
            if ica.get("demographics"):
                brand_parts.append(f"Target Audience: {json.dumps(ica['demographics'])}")
        if profile_snapshot.get("offer"):
            offer = profile_snapshot["offer"]
            if offer.get("name"):
                brand_parts.append(f"Offer: {offer['name']}")
        if profile_snapshot.get("messaging"):
            msg = profile_snapshot["messaging"]
            if msg.get("key_phrases"):
                brand_parts.append(f"Key Phrases: {', '.join(msg['key_phrases'][:5])}")

        if brand_parts:
            parts.append("\n## Creator's Brand Profile\n" + "\n".join(brand_parts))

    return "\n".join(parts)


def _get_opening_message(settings: Dict[str, Any]) -> str:
    """Generate the opening AI message based on content settings."""
    objective = settings.get("objective", "")
    content_type = settings.get("content_type", "")
    platforms = settings.get("platforms", [])
    tone = settings.get("tone", "")

    platform_str = ", ".join(platforms) if platforms else "your chosen platform"

    return (
        f"I'm ready to help you create content. Based on your settings, "
        f"we're working on **{content_type or 'a content piece'}** "
        f"for **{platform_str}**"
        f"{f' with a **{objective}** goal' if objective else ''}.\n\n"
        f"What topic or idea do you want to explore? You can:\n"
        f"- Share a topic and I'll research angles and hooks\n"
        f"- Paste a rough draft and I'll refine it\n"
        f"- Ask me to brainstorm ideas based on your brand pillars\n"
        f"- Give me a reference video/post and I'll create something similar in your voice"
    )


# ── Endpoints ────────────────────────────────────────────


@router.post("/message", response_model=ContentChatResponse)
async def send_message(
    body: ContentChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message in the content chat and get an AI response."""
    admin = get_admin_client()

    # Load brand profile if brand_id provided
    profile_snapshot = {}
    content_tier = ""
    if body.brand_id:
        brand_resp = (
            admin.table("personal_brands")
            .select("id, profile_json, model_tier")
            .eq("id", body.brand_id)
            .eq("user_id", user.id)
            .execute()
        )
        if brand_resp.data:
            profile_snapshot = brand_resp.data[0].get("profile_json", {}) or {}
            content_tier = brand_resp.data[0].get("model_tier", "") or ""

    # Find or create chat
    if body.chat_id:
        chat_resp = (
            admin.table("brand_chats")
            .select("*")
            .eq("id", body.chat_id)
            .eq("user_id", user.id)
            .execute()
        )
        if not chat_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content chat not found",
            )
        chat_row = chat_resp.data[0]
    else:
        # Create new content chat
        settings = body.settings or {}
        opening = _get_opening_message(settings)
        insert_data = {
            "user_id": user.id,
            "module": "content",
            "messages": [{"role": "assistant", "content": opening}],
            "extracted": {"settings": settings},
            "status": "active",
        }
        if body.brand_id:
            insert_data["brand_id"] = body.brand_id

        new_chat = (
            admin.table("brand_chats")
            .insert(insert_data)
            .execute()
        )
        chat_row = new_chat.data[0]

    messages = chat_row.get("messages", [])
    settings = chat_row.get("extracted", {}).get("settings", body.settings or {})

    # Append user message
    messages.append({"role": "user", "content": body.message})

    # Build LLM messages
    system_msg = _build_system_message(settings, profile_snapshot)
    llm_messages = [{"role": "system", "content": system_msg}]

    # Add conversation history (limit to last 20 messages to stay within context)
    for m in messages[-20:]:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    # Call LLM with the brand's model tier
    from worker.graph.llm import get_model_for_chat
    content_model = get_model_for_chat(content_tier)

    llm = get_llm_client()
    try:
        response = llm.chat(
            messages=llm_messages,
            model=content_model,
            temperature=0.7,
            max_tokens=3000,
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM API quota exceeded. Please check your billing or switch to a lower-cost model tier.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {error_msg[:200]}",
        )

    reply = response.get("content", "").strip()
    if not reply:
        reply = "I'm having trouble generating a response right now. Could you try rephrasing?"

    # Append assistant reply
    messages.append({"role": "assistant", "content": reply})

    # Auto-generate title from first user message
    title = chat_row.get("title")
    if not title:
        first_user_msg = body.message[:80]
        title = first_user_msg + ("..." if len(body.message) > 80 else "")

    # Update chat row
    admin.table("brand_chats").update({
        "messages": messages,
        "title": title,
    }).eq("id", chat_row["id"]).execute()

    return ContentChatResponse(
        reply=reply,
        chat_id=chat_row["id"],
        messages=[ContentChatMessage(role=m["role"], content=m["content"]) for m in messages],
    )


@router.get("/chats", response_model=List[ContentChatListItem])
async def list_content_chats(
    brand_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """List all content chats for the user."""
    admin = get_admin_client()

    query = (
        admin.table("brand_chats")
        .select("id, title, messages, extracted, created_at, status")
        .eq("user_id", user.id)
        .eq("module", "content")
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.order("created_at", desc=True).execute()

    items = []
    for row in resp.data:
        msgs = row.get("messages", [])
        # Get first user message as preview
        preview = ""
        for m in msgs:
            if m.get("role") == "user":
                preview = m["content"][:100]
                break
        if not preview and msgs:
            preview = msgs[0].get("content", "")[:100]

        items.append(ContentChatListItem(
            chat_id=row["id"],
            title=row.get("title"),
            preview=preview,
            settings=row.get("extracted", {}).get("settings", {}),
            created_at=row["created_at"],
            message_count=len(msgs),
        ))

    return items


@router.get("/chats/{chat_id}", response_model=ContentChatHistory)
async def get_content_chat(
    chat_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a specific content chat with full history."""
    admin = get_admin_client()

    resp = (
        admin.table("brand_chats")
        .select("id, messages, extracted, created_at")
        .eq("id", chat_id)
        .eq("user_id", user.id)
        .eq("module", "content")
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content chat not found",
        )

    row = resp.data[0]
    return ContentChatHistory(
        chat_id=row["id"],
        messages=[
            ContentChatMessage(role=m["role"], content=m["content"])
            for m in row.get("messages", [])
        ],
        settings=row.get("extracted", {}).get("settings", {}),
        created_at=row["created_at"],
    )


@router.delete("/chats/{chat_id}")
async def delete_content_chat(
    chat_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a content chat."""
    admin = get_admin_client()

    resp = (
        admin.table("brand_chats")
        .select("id")
        .eq("id", chat_id)
        .eq("user_id", user.id)
        .eq("module", "content")
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content chat not found",
        )

    admin.table("brand_chats").delete().eq("id", chat_id).execute()
    return {"message": "Chat deleted"}
