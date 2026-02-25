"""Agent Training Service.

Manages the trainable aspects of the AI agent:
  - Loading active prompt configs (admin-editable)
  - Loading training examples for few-shot context
  - Loading user feedback patterns for improvement
  - Loading custom instructions per user per brand
  - Building prompt additions from all training data

This service is the bridge between the DB-stored training data
and the system prompt that gets sent to the LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.deps import get_admin_client

logger = logging.getLogger("app.services.agent_training")


# ── Prompt Config Loading ──────────────────────────────────────


def get_active_prompt_configs() -> Dict[str, str]:
    """Load all active prompt config sections from the DB.

    Returns a dict mapping config_key -> content.
    Falls back to empty dict if DB is unreachable.
    """
    try:
        sb = get_admin_client()
        resp = (
            sb.table("agent_training_config")
            .select("config_key, content")
            .eq("is_active", True)
            .execute()
        )
        return {row["config_key"]: row["content"] for row in (resp.data or [])}
    except Exception as e:
        logger.warning("Failed to load prompt configs: %s", e)
        return {}


def get_prompt_config(config_key: str) -> Optional[str]:
    """Load a single prompt config by key. Returns None if not found."""
    try:
        sb = get_admin_client()
        resp = (
            sb.table("agent_training_config")
            .select("content")
            .eq("config_key", config_key)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]["content"]
        return None
    except Exception as e:
        logger.warning("Failed to load prompt config %s: %s", config_key, e)
        return None


def get_pushback_templates() -> Dict[str, str]:
    """Load all active pushback templates from the DB.

    Returns a dict mapping config_key (without 'pushback_' prefix) -> content.
    """
    try:
        sb = get_admin_client()
        resp = (
            sb.table("agent_training_config")
            .select("config_key, content")
            .eq("config_type", "pushback")
            .eq("is_active", True)
            .execute()
        )
        result = {}
        for row in (resp.data or []):
            key = row["config_key"]
            if key.startswith("pushback_"):
                key = key[len("pushback_"):]
            result[key] = row["content"]
        return result
    except Exception as e:
        logger.warning("Failed to load pushback templates: %s", e)
        return {}


# ── Training Examples Loading ──────────────────────────────────


def get_training_examples(
    category: Optional[str] = None,
    module: Optional[str] = None,
    field: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Load active training examples with optional filters.

    Used to inject few-shot examples into the system prompt
    for the current field/module being worked on.
    """
    try:
        sb = get_admin_client()
        query = (
            sb.table("agent_training_examples")
            .select("*")
            .eq("is_active", True)
        )
        if category:
            query = query.eq("category", category)
        if module:
            query = query.eq("module", module)
        if field:
            query = query.eq("field", field)

        query = query.order("created_at", desc=True).limit(limit)
        resp = query.execute()
        return resp.data or []
    except Exception as e:
        logger.warning("Failed to load training examples: %s", e)
        return []


def format_examples_for_prompt(
    examples: List[Dict[str, Any]],
    max_examples: int = 3,
) -> str:
    """Format training examples into a prompt-ready string.

    Limits to max_examples to avoid bloating the context window.
    """
    if not examples:
        return ""

    lines = ["\n--- TRAINING EXAMPLES (respond like these) ---"]

    for i, ex in enumerate(examples[:max_examples]):
        category = ex.get("category", "example")
        user_input = ex.get("user_input", "")
        ideal = ex.get("ideal_response", "")
        notes = ex.get("context_notes", "")

        lines.append(f"\nExample {i + 1} ({category}):")
        if user_input:
            lines.append(f"User: {user_input}")
        if ideal:
            lines.append(f"Ideal Response: {ideal}")
        if notes:
            lines.append(f"Why: {notes}")

    return "\n".join(lines)


# ── User Feedback Loading ──────────────────────────────────────


def get_user_feedback_patterns(
    user_id: str,
    brand_id: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Load user feedback patterns to inform AI behavior.

    Returns a summary of what the user liked/disliked
    so the AI can adjust its approach.
    """
    try:
        sb = get_admin_client()
        query = (
            sb.table("agent_feedback")
            .select("feedback_type, feedback_text, response_metadata")
            .eq("user_id", user_id)
        )
        if brand_id:
            query = query.eq("brand_id", brand_id)

        query = query.order("created_at", desc=True).limit(limit)
        resp = query.execute()

        if not resp.data:
            return {"has_feedback": False}

        # Aggregate feedback
        thumbs_up = 0
        thumbs_down = 0
        corrections = []
        voice_issues = []

        for row in resp.data:
            ft = row.get("feedback_type")
            if ft == "thumbs_up":
                thumbs_up += 1
            elif ft == "thumbs_down":
                thumbs_down += 1
            elif ft == "correction" and row.get("feedback_text"):
                corrections.append(row["feedback_text"])
            elif ft == "voice_mismatch" and row.get("feedback_text"):
                voice_issues.append(row["feedback_text"])

        return {
            "has_feedback": True,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "corrections": corrections[:5],
            "voice_issues": voice_issues[:5],
        }
    except Exception as e:
        logger.warning("Failed to load user feedback: %s", e)
        return {"has_feedback": False}


def format_feedback_for_prompt(feedback: Dict[str, Any]) -> str:
    """Format user feedback patterns into a prompt addition.

    Only included if there is meaningful feedback to act on.
    """
    if not feedback.get("has_feedback"):
        return ""

    lines = ["\n--- USER PREFERENCES (learned from feedback) ---"]

    corrections = feedback.get("corrections", [])
    voice_issues = feedback.get("voice_issues", [])

    if corrections:
        lines.append("\nUser corrections (avoid these patterns):")
        for c in corrections:
            lines.append(f"  - {c}")

    if voice_issues:
        lines.append("\nVoice mismatch reports (adjust tone accordingly):")
        for v in voice_issues:
            lines.append(f"  - {v}")

    thumbs_up = feedback.get("thumbs_up", 0)
    thumbs_down = feedback.get("thumbs_down", 0)
    total = thumbs_up + thumbs_down
    if total > 3:
        satisfaction = int(thumbs_up / total * 100)
        lines.append(f"\nUser satisfaction: {satisfaction}% ({thumbs_up}/{total} positive)")

    return "\n".join(lines) if len(lines) > 1 else ""


# ── Custom Instructions Loading ─────────────────────────────────


def get_custom_instructions(
    user_id: str,
    brand_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Load custom instructions for a user/brand combo."""
    try:
        sb = get_admin_client()
        query = (
            sb.table("agent_custom_instructions")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
        )
        if brand_id:
            query = query.eq("brand_id", brand_id)

        query = query.limit(1)
        resp = query.execute()

        if resp.data:
            return resp.data[0]
        return None
    except Exception as e:
        logger.warning("Failed to load custom instructions: %s", e)
        return None


def format_instructions_for_prompt(
    instructions: Optional[Dict[str, Any]],
) -> str:
    """Format custom instructions into a prompt addition."""
    if not instructions:
        return ""

    lines = ["\n--- USER CUSTOM INSTRUCTIONS (always follow) ---"]

    text = instructions.get("instructions", "").strip()
    if text:
        lines.append(text)

    tone = instructions.get("tone_preference")
    if tone:
        lines.append(f"\nPreferred tone: {tone}")

    avoid = instructions.get("avoid_topics", [])
    if avoid:
        lines.append("\nTopics to AVOID: " + ", ".join(avoid))

    focus = instructions.get("focus_areas", [])
    if focus:
        lines.append("\nAreas to FOCUS ON: " + ", ".join(focus))

    return "\n".join(lines) if len(lines) > 1 else ""


# ── Combined Prompt Builder ─────────────────────────────────────


def build_training_context(
    user_id: str,
    brand_id: Optional[str] = None,
    current_module: Optional[str] = None,
    current_field: Optional[str] = None,
) -> str:
    """Build the complete training context to append to the system prompt.

    Combines:
    1. Relevant training examples for the current field
    2. User feedback patterns
    3. Custom instructions

    Returns a string to be appended to the system prompt.
    """
    parts = []

    # 1. Training examples for the current field
    examples = get_training_examples(
        module=current_module,
        field=current_field,
        limit=3,
    )
    # Also get general good response examples
    if not examples:
        examples = get_training_examples(
            category="good_response",
            limit=3,
        )

    example_text = format_examples_for_prompt(examples)
    if example_text:
        parts.append(example_text)

    # 2. User feedback patterns
    feedback = get_user_feedback_patterns(user_id, brand_id)
    feedback_text = format_feedback_for_prompt(feedback)
    if feedback_text:
        parts.append(feedback_text)

    # 3. Custom instructions
    instructions = get_custom_instructions(user_id, brand_id)
    instructions_text = format_instructions_for_prompt(instructions)
    if instructions_text:
        parts.append(instructions_text)

    return "\n\n".join(parts)
