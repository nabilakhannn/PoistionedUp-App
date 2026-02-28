"""QA Review Service: content quality assurance engine.

Two-phase scoring system:
  Phase 1: Rule-based checks (fast, deterministic) — forbidden words, hard bans,
           length validation, AI-tells detection.
  Phase 2: LLM-based scoring (nuanced, contextual) — voice alignment, hook strength,
           virality potential, goal alignment.

Scores are aggregated into a 0-100 overall score with weighted dimensions:
  - Voice: 25%, Hook: 20%, Virality: 20%, AI-Tell: 15%, Structure: 10%, Goal: 10%

Verdicts: pass (>= 80), revise (50-79), fail (< 50).
Auto-revision: up to 2 cycles, then escalates to human.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.deps import get_admin_client
from app.schemas.qa_review import (
    QA_PASS_THRESHOLD,
    QA_REVISE_THRESHOLD,
    QA_MAX_REVISIONS,
    QAReviewRequest,
    QAScoreBreakdown,
    QAReviewResult,
    QAIssue,
    QARiskFlag,
    QAStats,
    QAReviewOut,
    SCORE_WEIGHTS,
)

logger = logging.getLogger("app.services.qa_review")


# ── Forbidden words list (parsed from writing_style.py) ───────────
# These are extracted at import time for fast O(1) lookup in rule checks.

_FORBIDDEN_WORDS_RAW = [
    "elevate", "delve", "robust", "innovative", "groundbreaking",
    "cutting edge", "practical solutions", "optimize", "unlock",
    "supercharge", "fuel", "empower", "boost", "unleash", "harness",
    "leverage", "game-changer", "seamless", "streamline", "synergy",
    "holistic", "ecosystem", "paradigm", "deep dive", "journey",
    "landscape", "navigate", "genuinely captivating",
    "extraordinary effort", "striking the perfect pose",
    "hidden portal", "fabric of space", "built to last",
    "quietly captures", "stirring into my soul", "echo is airborne",
    "record breaking event", "redefines what we thought we knew",
    "kiss that broke the timeline",
]

# Platform length limits
_PLATFORM_LIMITS = {
    "twitter": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "tiktok": 2200,
}


# ══════════════════════════════════════════════════════════════════
# Phase 1: Rule-Based Checks
# ══════════════════════════════════════════════════════════════════

def _run_rule_checks(
    content_text: str,
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    """Run fast, deterministic rule checks on content text.

    Returns dict with issues found and preliminary scores for
    ai_tell and structure dimensions.
    """
    issues: List[Dict[str, str]] = []
    text_lower = content_text.lower()

    # ── 1. Forbidden words ────────────────────────────────────
    forbidden_found = []
    for word in _FORBIDDEN_WORDS_RAW:
        if word.lower() in text_lower:
            forbidden_found.append(word)

    if forbidden_found:
        issues.append({
            "category": "ai_tell",
            "severity": "critical" if len(forbidden_found) >= 3 else "warning",
            "detail": f"Forbidden words detected: {', '.join(forbidden_found[:5])}",
        })

    # ── 2. Hard bans: em dash, semicolons, reversals ──────────
    em_dash_count = content_text.count("\u2014") + content_text.count(" - ")
    if em_dash_count > 0:
        issues.append({
            "category": "ai_tell",
            "severity": "critical",
            "detail": f"Em dash or fake dash detected ({em_dash_count} instances). Split into separate sentences.",
        })

    semicolon_count = content_text.count(";")
    if semicolon_count > 0:
        issues.append({
            "category": "ai_tell",
            "severity": "warning",
            "detail": f"Semicolons detected ({semicolon_count}). Use periods or commas instead.",
        })

    reversal_patterns = [
        r"(?:it\s+is\s+)?not\s+just\s+.{3,40},?\s+it\s+is",
        r"not\s+just\s+about\s+.{3,40},?\s+it.s\s+about",
    ]
    for pattern in reversal_patterns:
        if re.search(pattern, text_lower):
            issues.append({
                "category": "ai_tell",
                "severity": "critical",
                "detail": "Reversal template detected ('not just X, it is Y'). Rewrite directly.",
            })
            break

    # ── 3. Length validation ──────────────────────────────────
    structure_issues: List[Dict[str, str]] = []
    content_len = len(content_text)

    if content_len < 20:
        structure_issues.append({
            "category": "structure",
            "severity": "critical",
            "detail": "Content too short (< 20 characters).",
        })

    if platform and platform in _PLATFORM_LIMITS:
        limit = _PLATFORM_LIMITS[platform]
        if content_len > limit:
            structure_issues.append({
                "category": "structure",
                "severity": "warning",
                "detail": f"Content exceeds {platform} limit ({content_len}/{limit} chars).",
            })

    # ── 4. AI-tells checklist (programmatic subset) ───────────
    # Check for tidy lists of three
    triple_pattern = re.findall(r"(?:^|\n)\s*[-•*]\s+.+(?:\n\s*[-•*]\s+.+){2}(?:\n|$)", content_text)
    if len(triple_pattern) > 1:
        issues.append({
            "category": "ai_tell",
            "severity": "warning",
            "detail": "Multiple tidy lists of three detected. Use varied counts.",
        })

    # Check for generic praise patterns
    praise_patterns = [
        r"genuinely\s+(?:captivat|inspir|transform)",
        r"extraordinary\s+(?:effort|work|piece)",
        r"honest\s+and\s+vivid",
        r"striking\s+the\s+perfect",
    ]
    for pattern in praise_patterns:
        if re.search(pattern, text_lower):
            issues.append({
                "category": "ai_tell",
                "severity": "warning",
                "detail": "Generic AI-sounding praise detected. Use specific observations.",
            })
            break

    # ── 5. Calculate rule-based scores ────────────────────────
    ai_tell_deductions = 0
    for issue in issues:
        if issue["category"] == "ai_tell":
            ai_tell_deductions += 20 if issue["severity"] == "critical" else 10

    ai_tell_score = max(0, 100 - ai_tell_deductions)

    structure_deductions = 0
    for issue in structure_issues:
        structure_deductions += 30 if issue["severity"] == "critical" else 15

    structure_score = max(0, 100 - structure_deductions)

    all_issues = issues + structure_issues

    return {
        "issues": all_issues,
        "rule_scores": {
            "ai_tell": ai_tell_score,
            "structure": structure_score,
        },
        "forbidden_found": forbidden_found,
    }


# ══════════════════════════════════════════════════════════════════
# Phase 2: LLM-Based Scoring
# ══════════════════════════════════════════════════════════════════

_QA_SYSTEM_PROMPT = """\
You are a world-class content quality analyst for a personal branding platform.

Your job is to score a piece of content on 6 dimensions (0-100 each):

1. **voice_score** (0-100): How well does this match the creator's voice DNA? \
Consider tone, sentence style, vocabulary, personality traits, and signature phrases. \
Score 100 if it sounds exactly like the creator wrote it. Score 0 if it sounds generic/AI-generated.

2. **hook_score** (0-100): How strong is the opening hook? Does it stop the scroll? \
Consider: pattern interrupt, curiosity gap, emotional trigger, specificity. \
Score 100 for an irresistible hook. Score 0 for a bland opening.

3. **structure_score** (0-100): Is the content well-structured for the target platform? \
Consider: flow, formatting, completeness, CTA, readability. \
Score 100 for perfect structure. Score 0 for incoherent mess.

4. **virality_score** (0-100): How likely is this to perform well based on historical patterns? \
Consider: topic relevance, hook type match to top performers, emotional resonance, \
shareability, engagement triggers. Score 100 for viral potential. Score 0 for guaranteed flop.

5. **goal_alignment_score** (0-100): Does this content advance the creator's stated goals \
and content pillars? Score 100 for perfect alignment. Score 0 for completely off-brand.

6. **ai_tell_score** (0-100): How clean is this from AI-tells? Check for em dashes, \
reversal templates, forbidden words, generic praise, corporate filler, stock language. \
Score 100 if it reads 100% human. Score 0 if it screams AI.

IMPORTANT: Be strict. Most content should score 60-80. Only truly exceptional content gets 90+. \
Only terrible content scores below 30.

You MUST respond with valid JSON matching this exact schema:
{
    "voice_score": <int 0-100>,
    "hook_score": <int 0-100>,
    "structure_score": <int 0-100>,
    "virality_score": <int 0-100>,
    "goal_alignment_score": <int 0-100>,
    "ai_tell_score": <int 0-100>,
    "feedback": "<2-3 sentence summary of key findings>",
    "issues": [{"category": "<voice|hook|structure|ai_tell|virality|goal>", "severity": "<critical|warning|info>", "detail": "<specific issue>"}],
    "risk_flags": [{"type": "<medical_claim|legal_risk|unverified_stat|financial_advice|offensive>", "detail": "<what was flagged>"}]
}
"""


def _build_qa_user_prompt(
    content_text: str,
    brand_profile: Optional[Dict[str, Any]],
    voice_dna: Optional[Dict[str, Any]],
    performance_context: Optional[str],
    platform: Optional[str],
    rule_issues: List[Dict[str, str]],
) -> str:
    """Build the USER prompt with all context for LLM scoring."""
    parts = []

    # Content to review
    truncated = content_text[:10000]
    parts.append(f"## Content to Review\n\nPlatform: {platform or 'unknown'}\n\n```\n{truncated}\n```")

    # Brand profile context
    if brand_profile:
        profile_json = brand_profile.get("profile_json") or {}
        foundation = profile_json.get("foundation") or {}
        messaging = profile_json.get("messaging") or {}
        positioning = profile_json.get("positioning") or {}

        profile_parts = []
        if foundation.get("mission"):
            profile_parts.append(f"Mission: {foundation['mission']}")
        if foundation.get("90_day_goal"):
            profile_parts.append(f"90-day goal: {foundation['90_day_goal']}")
        if messaging.get("content_pillars"):
            pillars = messaging["content_pillars"]
            if isinstance(pillars, list):
                profile_parts.append(f"Content pillars: {', '.join(str(p) for p in pillars[:5])}")
            else:
                profile_parts.append(f"Content pillars: {pillars}")
        if positioning.get("positioning_statement"):
            profile_parts.append(f"Positioning: {positioning['positioning_statement']}")

        if profile_parts:
            parts.append("## Brand Profile\n\n" + "\n".join(profile_parts))

    # Voice DNA context
    if voice_dna:
        voice_parts = []
        if voice_dna.get("tone"):
            voice_parts.append(f"Tone: {voice_dna['tone']}")
        if voice_dna.get("sentence_style"):
            voice_parts.append(f"Sentence style: {voice_dna['sentence_style']}")
        if voice_dna.get("vocabulary_level"):
            voice_parts.append(f"Vocabulary: {voice_dna['vocabulary_level']}")
        if voice_dna.get("personality_traits"):
            traits = voice_dna["personality_traits"]
            if isinstance(traits, list):
                voice_parts.append(f"Personality: {', '.join(str(t) for t in traits[:5])}")
        if voice_dna.get("signature_phrases"):
            phrases = voice_dna["signature_phrases"]
            if isinstance(phrases, list):
                voice_parts.append(f"Signature phrases: {', '.join(str(p) for p in phrases[:5])}")

        if voice_parts:
            parts.append("## Creator's Voice DNA\n\n" + "\n".join(voice_parts))

    # Performance context
    if performance_context:
        parts.append(f"## Performance Data\n\n{performance_context[:3000]}")

    # Rule-based issues already found
    if rule_issues:
        rule_summary = "\n".join(f"- [{i['severity']}] {i['detail']}" for i in rule_issues[:10])
        parts.append(f"## Pre-Scan Issues Found\n\nThese issues were detected programmatically:\n{rule_summary}")

    parts.append(
        "\n\nScore this content strictly on all 6 dimensions. "
        "Return your analysis as JSON."
    )

    return "\n\n".join(parts)


def _run_llm_scoring(
    content_text: str,
    brand_profile: Optional[Dict[str, Any]],
    voice_dna: Optional[Dict[str, Any]],
    performance_context: Optional[str],
    platform: Optional[str],
    rule_issues: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Run LLM-based content scoring. Returns parsed scores dict."""
    try:
        from worker.graph.llm import get_llm_client, parse_json_response, get_model_for_step

        client = get_llm_client()
        model = get_model_for_step("testing")

        user_prompt = _build_qa_user_prompt(
            content_text, brand_profile, voice_dna,
            performance_context, platform, rule_issues,
        )

        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": _QA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        result = parse_json_response(response)

        # Clamp all scores to 0-100
        for key in ("voice_score", "hook_score", "structure_score",
                     "virality_score", "goal_alignment_score", "ai_tell_score"):
            if key in result:
                result[key] = max(0, min(100, int(result[key])))

        return result

    except Exception as e:
        logger.error("LLM QA scoring failed: %s", e)
        # Fallback: return neutral scores so rule-based checks still work
        return {
            "voice_score": 50,
            "hook_score": 50,
            "structure_score": 50,
            "virality_score": 50,
            "goal_alignment_score": 50,
            "ai_tell_score": 50,
            "feedback": "LLM scoring unavailable. Rule-based checks only.",
            "issues": [],
            "risk_flags": [],
        }


# ══════════════════════════════════════════════════════════════════
# Phase 3: Score Aggregation
# ══════════════════════════════════════════════════════════════════

def _aggregate_scores(
    rule_scores: Dict[str, int],
    llm_scores: Dict[str, Any],
) -> Tuple[int, QAScoreBreakdown]:
    """Combine rule-based and LLM scores into weighted overall score.

    For ai_tell and structure: takes the MINIMUM of rule-based and LLM
    (conservative approach — if either engine detects problems, score drops).
    For other dimensions: uses LLM score directly.
    """
    # Conservative minimum for dimensions with rule-based checks
    ai_tell = min(rule_scores.get("ai_tell", 100), llm_scores.get("ai_tell_score", 50))
    structure = min(rule_scores.get("structure", 100), llm_scores.get("structure_score", 50))

    # LLM-only dimensions
    voice = llm_scores.get("voice_score", 50)
    hook = llm_scores.get("hook_score", 50)
    virality = llm_scores.get("virality_score", 50)
    goal_alignment = llm_scores.get("goal_alignment_score", 50)

    breakdown = QAScoreBreakdown(
        voice_score=voice,
        hook_score=hook,
        structure_score=structure,
        ai_tell_score=ai_tell,
        virality_score=virality,
        goal_alignment_score=goal_alignment,
    )

    # Weighted average
    overall = round(
        voice * SCORE_WEIGHTS["voice"]
        + hook * SCORE_WEIGHTS["hook"]
        + virality * SCORE_WEIGHTS["virality"]
        + ai_tell * SCORE_WEIGHTS["ai_tell"]
        + structure * SCORE_WEIGHTS["structure"]
        + goal_alignment * SCORE_WEIGHTS["goal_alignment"]
    )
    overall = max(0, min(100, overall))

    return overall, breakdown


def _determine_verdict(score: int) -> str:
    """Map overall score to verdict string."""
    if score >= QA_PASS_THRESHOLD:
        return "pass"
    elif score >= QA_REVISE_THRESHOLD:
        return "revise"
    else:
        return "fail"


# ══════════════════════════════════════════════════════════════════
# Auto-Revision
# ══════════════════════════════════════════════════════════════════

def _trigger_revision(
    user_id: str,
    review_id: str,
    review_feedback: str,
    review_issues: List[Dict[str, str]],
    content_ref_type: str,
    content_ref_id: Optional[str],
    sb: Any,
) -> bool:
    """Create a revision task for the Copywriter agent.

    Returns True if revision was created, False if skipped.
    """
    try:
        issue_summary = "\n".join(
            f"- [{i.get('severity', 'warning')}] {i.get('detail', '')}"
            for i in review_issues[:8]
        )

        task_id = str(uuid.uuid4())
        brief = (
            f"QA Review failed. Please revise this content based on the following feedback:\n\n"
            f"{review_feedback}\n\n"
            f"Issues found:\n{issue_summary}\n\n"
            f"Source: {content_ref_type}"
            + (f" (ID: {content_ref_id})" if content_ref_id else "")
        )

        sb.table("agent_tasks").insert({
            "id": task_id,
            "user_id": user_id,
            "title": f"QA Revision Required",
            "description": brief,
            "status": "assigned",
            "priority": "P1",
            "assignee_id": "copywriter",
            "tags": [
                "type:qa_revision",
                f"qa_review_id:{review_id}",
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        logger.info("Created QA revision task %s for review %s", task_id, review_id)
        return True

    except Exception as e:
        logger.error("Failed to create revision task: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════════

def review_content(
    user_id: str,
    request: QAReviewRequest,
    sb: Any,
) -> QAReviewResult:
    """Review content and return a scored QA result.

    This is the main entry point for all QA reviews. It:
    1. Loads brand context (profile, voice DNA, performance data)
    2. Runs rule-based checks (forbidden words, hard bans, length)
    3. Runs LLM-based scoring (voice, hook, virality, goal alignment)
    4. Aggregates into overall score + verdict
    5. Persists to qa_reviews table
    6. Triggers auto-revision if needed
    """
    # ── Load context ──────────────────────────────────────────
    brand_profile = None
    voice_dna = None
    performance_context = None

    try:
        # Try to load brand profile
        brand_id = request.brand_id
        if not brand_id:
            # Get active brand
            brand_resp = (
                sb.table("personal_brands")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            if brand_resp.data:
                brand_profile = brand_resp.data[0]
                brand_id = brand_profile["id"]
        else:
            brand_resp = (
                sb.table("personal_brands")
                .select("*")
                .eq("id", brand_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if brand_resp.data:
                brand_profile = brand_resp.data[0]

        # Load voice DNA
        if brand_id:
            try:
                profile_resp = (
                    sb.table("profiles")
                    .select("self_voice_dna")
                    .eq("id", user_id)
                    .limit(1)
                    .execute()
                )
                if profile_resp.data and profile_resp.data[0].get("self_voice_dna"):
                    voice_dna = profile_resp.data[0]["self_voice_dna"]
            except Exception:
                pass  # Voice DNA is optional enhancement

        # Load performance context
        try:
            from app.services.performance_analytics import get_performance_context
            posts_resp = (
                sb.table("content_posts")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            if posts_resp.data:
                performance_context = get_performance_context(posts_resp.data, request.platform)
        except Exception:
            pass  # Performance context is optional enhancement

    except Exception as e:
        logger.warning("Failed to load QA context: %s", e)

    # ── Phase 1: Rule-based checks ────────────────────────────
    rule_results = _run_rule_checks(request.content_text, request.platform)

    # ── Phase 2: LLM scoring ─────────────────────────────────
    llm_results = _run_llm_scoring(
        request.content_text,
        brand_profile,
        voice_dna,
        performance_context,
        request.platform,
        rule_results["issues"],
    )

    # ── Phase 3: Aggregate ────────────────────────────────────
    overall_score, breakdown = _aggregate_scores(
        rule_results["rule_scores"],
        llm_results,
    )

    verdict = _determine_verdict(overall_score)
    feedback = llm_results.get("feedback", "Review complete.")

    # Merge issues from both phases (deduplicate by detail)
    seen_details = set()
    merged_issues = []
    for issue in rule_results["issues"] + llm_results.get("issues", []):
        detail = issue.get("detail", "")
        if detail not in seen_details:
            seen_details.add(detail)
            merged_issues.append(issue)

    risk_flags = llm_results.get("risk_flags", [])

    # ── Check revision number ─────────────────────────────────
    revision_number = 0
    if request.content_ref_id:
        prev_resp = (
            sb.table("qa_reviews")
            .select("revision_number")
            .eq("content_ref_type", request.content_ref_type)
            .eq("content_ref_id", request.content_ref_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if prev_resp.data:
            revision_number = prev_resp.data[0].get("revision_number", 0) + 1

    # ── Persist ───────────────────────────────────────────────
    review_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    row = {
        "id": review_id,
        "user_id": user_id,
        "brand_id": request.brand_id,
        "content_ref_type": request.content_ref_type,
        "content_ref_id": request.content_ref_id,
        "content_text": request.content_text[:50000],
        "platform": request.platform,
        "overall_score": overall_score,
        "voice_score": breakdown.voice_score,
        "hook_score": breakdown.hook_score,
        "structure_score": breakdown.structure_score,
        "ai_tell_score": breakdown.ai_tell_score,
        "virality_score": breakdown.virality_score,
        "goal_alignment_score": breakdown.goal_alignment_score,
        "verdict": verdict,
        "feedback": feedback,
        "issues": merged_issues,
        "risk_flags": risk_flags,
        "revision_number": min(revision_number, 5),
        "reviewed_by": "system",
        "created_at": now_iso,
    }
    sb.table("qa_reviews").insert(row).execute()

    # ── Auto-revision ─────────────────────────────────────────
    revision_triggered = False
    if verdict in ("revise", "fail") and revision_number < QA_MAX_REVISIONS:
        revision_triggered = _trigger_revision(
            user_id, review_id, feedback, merged_issues,
            request.content_ref_type, request.content_ref_id, sb,
        )

    # ── Build result ──────────────────────────────────────────
    qa_issues = [
        QAIssue(
            category=i.get("category", "structure"),
            severity=i.get("severity", "warning"),
            detail=i.get("detail", ""),
        )
        for i in merged_issues
        if i.get("category") in {"voice", "hook", "structure", "ai_tell", "virality", "goal"}
    ]

    qa_risk_flags = [
        QARiskFlag(type=r.get("type", "unknown"), detail=r.get("detail", ""))
        for r in risk_flags
    ]

    return QAReviewResult(
        id=review_id,
        overall_score=overall_score,
        scores=breakdown,
        verdict=verdict,
        feedback=feedback,
        issues=qa_issues,
        risk_flags=qa_risk_flags,
        revision_number=min(revision_number, 5),
        revision_triggered=revision_triggered,
        created_at=now_iso,
    )


# ══════════════════════════════════════════════════════════════════
# Stats & Listing
# ══════════════════════════════════════════════════════════════════

def get_qa_stats(
    user_id: str,
    days: int = 30,
    sb: Any = None,
) -> QAStats:
    """Aggregate QA stats for the dashboard."""
    if sb is None:
        sb = get_admin_client()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    resp = (
        sb.table("qa_reviews")
        .select("overall_score, voice_score, hook_score, virality_score, verdict, issues")
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
        .execute()
    )

    reviews = resp.data or []
    if not reviews:
        return QAStats()

    total = len(reviews)
    pass_count = sum(1 for r in reviews if r.get("verdict") == "pass")
    revise_count = sum(1 for r in reviews if r.get("verdict") == "revise")
    fail_count = sum(1 for r in reviews if r.get("verdict") == "fail")

    avg_score = sum(r.get("overall_score", 0) for r in reviews) / total
    avg_voice = sum(r.get("voice_score", 0) or 0 for r in reviews) / total
    avg_hook = sum(r.get("hook_score", 0) or 0 for r in reviews) / total
    avg_virality = sum(r.get("virality_score", 0) or 0 for r in reviews) / total

    # Common issues aggregation
    issue_counter: Counter = Counter()
    for r in reviews:
        for issue in (r.get("issues") or []):
            cat = issue.get("category", "unknown")
            issue_counter[cat] += 1

    common_issues = [
        {"category": cat, "count": count}
        for cat, count in issue_counter.most_common(10)
    ]

    return QAStats(
        total_reviews=total,
        pass_count=pass_count,
        revise_count=revise_count,
        fail_count=fail_count,
        avg_score=round(avg_score, 1),
        avg_voice_score=round(avg_voice, 1),
        avg_hook_score=round(avg_hook, 1),
        avg_virality_score=round(avg_virality, 1),
        common_issues=common_issues,
    )


def list_reviews(
    user_id: str,
    days: int = 30,
    verdict: Optional[str] = None,
    limit: int = 50,
    sb: Any = None,
) -> List[QAReviewOut]:
    """List recent QA reviews for the dashboard."""
    if sb is None:
        sb = get_admin_client()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    query = (
        sb.table("qa_reviews")
        .select("id, content_ref_type, content_ref_id, platform, overall_score, verdict, feedback, revision_number, created_at")
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if verdict:
        query = query.eq("verdict", verdict)

    resp = query.execute()

    return [
        QAReviewOut(
            id=r["id"],
            content_ref_type=r.get("content_ref_type", "freeform"),
            content_ref_id=r.get("content_ref_id"),
            platform=r.get("platform"),
            overall_score=r.get("overall_score", 0),
            verdict=r.get("verdict", "pending"),
            feedback=r.get("feedback"),
            revision_number=r.get("revision_number", 0),
            created_at=r.get("created_at", ""),
        )
        for r in (resp.data or [])
    ]


def get_review(
    review_id: str,
    user_id: str,
    sb: Any = None,
) -> Optional[Dict[str, Any]]:
    """Get a single QA review by ID."""
    if sb is None:
        sb = get_admin_client()

    resp = (
        sb.table("qa_reviews")
        .select("*")
        .eq("id", review_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    return resp.data[0] if resp.data else None
