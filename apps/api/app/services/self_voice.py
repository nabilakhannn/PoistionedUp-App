"""Self-Voice DNA service — builds a voice profile from the user's OWN
published content and detects drift when AI-generated content strays
too far from their natural writing style.

Unlike voice_analysis.py (which analyzes reference creator collections),
this analyzes content_posts the user has actually published themselves.

Key functions:
  - analyze_self_voice() — extract Voice DNA from top-performing published posts
  - check_voice_drift() — compare generated text against user's voice baseline
  - get_voice_baseline() — retrieve stored voice profile
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

logger = logging.getLogger("app.services.self_voice")

# Minimum published posts needed to build self-voice DNA
MIN_POSTS_FOR_VOICE = 10

SELF_VOICE_SYSTEM = """You are a writing style analyst. You study a creator's OWN published content
to extract their unique natural voice profile.

This is NOT reference content from other creators — this is the user's actual published work.
Your goal is to capture their authentic voice so AI-generated content can match it.

Analyze the provided posts and return a JSON object with EXACTLY these fields:
{
  "tone": "One sentence describing their overall tone",
  "sentence_style": "Their sentence structure pattern (length, complexity, fragments)",
  "vocabulary_level": "Their word choice style",
  "avg_sentence_length": 12.5,
  "hook_patterns": ["List of 3-5 hook types they naturally use"],
  "cta_patterns": ["List of 2-3 CTA styles they naturally use"],
  "signature_phrases": ["5-10 phrases or expressions unique to this creator"],
  "content_structure": "How they typically structure content",
  "personality_traits": ["3-5 personality traits visible in their writing"],
  "sample_hooks": ["5-10 actual hooks from their best posts, quoted exactly"]
}

Be specific. Quote actual patterns from the content. This is about THEIR voice, not generic advice."""


DRIFT_CHECK_SYSTEM = """You are a writing style comparator. You compare AI-generated text against
a creator's natural voice profile to detect drift.

You will receive:
1. The creator's Voice DNA profile (their natural style)
2. A piece of AI-generated content to check

Evaluate how closely the generated content matches their natural voice.

Return a JSON object with:
{
  "drift_score": 0.35,
  "drift_details": [
    "Specific observation about what differs from their natural voice"
  ],
  "recommendation": "A brief suggestion for how to bring the content closer to their voice"
}

drift_score: 0.0 = perfect match, 1.0 = completely different voice
Be specific about what's different. Reference their actual patterns.""" + HUMAN_WRITING_RULES


def analyze_self_voice(user_id: str) -> Dict[str, Any]:
    """Analyze the user's published content to extract their Self-Voice DNA.

    Uses their top-performing posts (by engagement) to build a voice
    profile that represents their authentic writing style.

    Returns the extracted voice DNA dict.
    Stores it in profiles.self_voice_dna.
    """
    from app.deps import get_admin_client
    admin = get_admin_client()

    # Fetch user's published posts with content
    resp = (
        admin.table("content_posts")
        .select("title, hook_used, content_body, platform, engagement_rate, performance_tier")
        .eq("user_id", user_id)
        .order("engagement_rate", desc=True)
        .limit(30)
        .execute()
    )
    posts = resp.data if resp.data else []

    if len(posts) < MIN_POSTS_FOR_VOICE:
        raise ValueError(
            f"Not enough published posts for voice analysis. "
            f"Found {len(posts)}, need at least {MIN_POSTS_FOR_VOICE}. "
            f"Log more posts in the Performance section first."
        )

    # Build content samples from posts
    samples = []
    for i, post in enumerate(posts):
        parts = []
        if post.get("title"):
            parts.append(f"Title: {post['title']}")
        if post.get("hook_used"):
            parts.append(f"Hook: {post['hook_used']}")
        if post.get("content_body"):
            # Take first 1000 chars to keep prompt manageable
            body = post["content_body"][:1000]
            parts.append(f"Content:\n{body}")
        if post.get("platform"):
            parts.append(f"Platform: {post['platform']}")
        if post.get("performance_tier"):
            parts.append(f"Performance: {post['performance_tier']}")

        if parts:
            samples.append(f"[Post {i + 1}]\n" + "\n".join(parts))

    user_prompt = (
        f"Analyze these {len(samples)} published posts from the creator.\n"
        f"Extract their natural Voice DNA.\n\n"
        + "\n\n---\n\n".join(samples)
        + "\n\nExtract the Voice DNA profile as JSON."
    )

    # Call LLM
    from worker.graph.llm import get_llm_client, parse_json_response
    llm = get_llm_client()

    response = llm.chat(
        messages=[
            {"role": "system", "content": SELF_VOICE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        model="gpt-4o",
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(response["content"])

    voice_dna = {
        "tone": result.get("tone", ""),
        "sentence_style": result.get("sentence_style", ""),
        "vocabulary_level": result.get("vocabulary_level", ""),
        "avg_sentence_length": result.get("avg_sentence_length"),
        "hook_patterns": result.get("hook_patterns", []),
        "cta_patterns": result.get("cta_patterns", []),
        "signature_phrases": result.get("signature_phrases", []),
        "content_structure": result.get("content_structure", ""),
        "personality_traits": result.get("personality_traits", []),
        "sample_hooks": result.get("sample_hooks", []),
        "posts_analyzed": len(samples),
    }

    # Store in profiles table
    admin.table("profiles").update({
        "self_voice_dna": voice_dna,
        "voice_drift_baseline": voice_dna,  # Use first analysis as baseline
    }).eq("user_id", user_id).execute()

    logger.info(
        "Self-Voice DNA extracted for user %s from %d posts",
        user_id, len(samples),
    )

    return voice_dna


def get_voice_baseline(user_id: str) -> Optional[Dict[str, Any]]:
    """Get the stored self-voice DNA for a user."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    resp = (
        admin.table("profiles")
        .select("self_voice_dna, voice_drift_baseline")
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        return None

    profile = resp.data[0]
    voice_dna = profile.get("self_voice_dna", {})

    if not voice_dna or not voice_dna.get("tone"):
        return None

    return voice_dna


def check_voice_drift(
    user_id: str,
    generated_text: str,
) -> Dict[str, Any]:
    """Compare AI-generated text against the user's natural voice.

    Returns drift analysis with score, details, and recommendations.
    """
    voice_dna = get_voice_baseline(user_id)

    if not voice_dna:
        return {
            "drift_score": 0.0,
            "drift_level": "unknown",
            "details": [],
            "recommendation": "No self-voice profile available. Analyze your voice first.",
            "baseline_available": False,
        }

    # Build voice profile summary for the LLM
    voice_summary = _format_voice_for_comparison(voice_dna)

    user_prompt = (
        f"CREATOR'S VOICE PROFILE:\n{voice_summary}\n\n"
        f"AI-GENERATED CONTENT TO CHECK:\n{generated_text[:3000]}\n\n"
        f"Analyze how closely this content matches the creator's natural voice."
    )

    from worker.graph.llm import get_llm_client, parse_json_response
    llm = get_llm_client()

    response = llm.chat(
        messages=[
            {"role": "system", "content": DRIFT_CHECK_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        model="gpt-4o-mini",  # Cheaper model fine for comparison
        temperature=0.2,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(response["content"])

    drift_score = min(1.0, max(0.0, float(result.get("drift_score", 0.5))))

    # Classify drift level
    if drift_score < 0.3:
        drift_level = "low"
    elif drift_score < 0.6:
        drift_level = "medium"
    else:
        drift_level = "high"

    return {
        "drift_score": drift_score,
        "drift_level": drift_level,
        "details": result.get("drift_details", []),
        "recommendation": result.get("recommendation", ""),
        "baseline_available": True,
    }


def _format_voice_for_comparison(voice_dna: Dict[str, Any]) -> str:
    """Format voice DNA as a readable summary for drift comparison."""
    parts = []

    if voice_dna.get("tone"):
        parts.append(f"Tone: {voice_dna['tone']}")
    if voice_dna.get("sentence_style"):
        parts.append(f"Sentence style: {voice_dna['sentence_style']}")
    if voice_dna.get("vocabulary_level"):
        parts.append(f"Vocabulary: {voice_dna['vocabulary_level']}")
    if voice_dna.get("content_structure"):
        parts.append(f"Structure: {voice_dna['content_structure']}")
    if voice_dna.get("hook_patterns"):
        parts.append(f"Hook patterns: {', '.join(voice_dna['hook_patterns'])}")
    if voice_dna.get("personality_traits"):
        parts.append(f"Personality: {', '.join(voice_dna['personality_traits'])}")
    if voice_dna.get("signature_phrases"):
        phrases = voice_dna["signature_phrases"][:8]
        parts.append(f"Signature phrases: {', '.join(phrases)}")
    if voice_dna.get("sample_hooks"):
        parts.append("Example hooks:")
        for hook in voice_dna["sample_hooks"][:5]:
            parts.append(f"  - {hook}")

    return "\n".join(parts)


def format_self_voice_instructions(voice_dna: Dict[str, Any]) -> str:
    """Format self-voice DNA as system prompt instructions.

    Same pattern as voice_analysis.format_voice_dna_instructions() but
    specifically for the user's OWN voice (not a reference creator).
    """
    if not voice_dna or not voice_dna.get("tone"):
        return ""

    parts = [
        "--- YOUR NATURAL WRITING VOICE ---",
        "This is YOUR authentic voice profile, extracted from your published content.",
        "Match this voice when generating content:",
        "",
    ]

    if voice_dna.get("tone"):
        parts.append(f"YOUR TONE: {voice_dna['tone']}")
    if voice_dna.get("sentence_style"):
        parts.append(f"YOUR SENTENCE STYLE: {voice_dna['sentence_style']}")
    if voice_dna.get("vocabulary_level"):
        parts.append(f"YOUR VOCABULARY: {voice_dna['vocabulary_level']}")
    if voice_dna.get("content_structure"):
        parts.append(f"YOUR STRUCTURE: {voice_dna['content_structure']}")
    if voice_dna.get("hook_patterns"):
        parts.append(f"YOUR HOOK PATTERNS: {', '.join(voice_dna['hook_patterns'])}")
    if voice_dna.get("signature_phrases"):
        phrases = voice_dna["signature_phrases"][:8]
        parts.append(f"YOUR SIGNATURE PHRASES (use naturally): {', '.join(phrases)}")
    if voice_dna.get("sample_hooks"):
        parts.append("")
        parts.append("YOUR ACTUAL HOOKS (match this style):")
        for hook in voice_dna["sample_hooks"][:5]:
            parts.append(f"  - {hook}")

    parts.append("")
    parts.append(
        "IMPORTANT: This is YOUR voice. Write as YOU would write — "
        "not in a generic AI tone."
    )

    return "\n".join(parts)
