"""Tool-Use Agent Engine — Slice 85.

Real multi-step agent reasoning using the Anthropic Messages API with tool definitions.
Claude Sonnet 4.6 acts as the reasoning engine; tools call out to Perplexity (web search),
Gemini (deep research synthesis), and Supabase (brand/playbook lookups).

LLM routing (cost-optimised):
  - Claude Sonnet 4.6  → all writing, hooks, copy, scripts, ad creative
  - Perplexity sonar-pro → web_search tool (real-time web + citations)
  - Gemini 2.0 Flash  → synthesize_research tool (multimodal, large context)
  - Rule-based         → score_content_quality (no LLM cost)

This module is intentionally independent of worker/graph/llm.py — it uses the
anthropic SDK directly to have full control over the tool-use loop.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import anthropic
import httpx

from app.config import settings
from app.deps import get_admin_client
from app.services.sdk_agents import AgentResult

logger = logging.getLogger("app.services.tool_use_agents")

# ── Constants ─────────────────────────────────────────────────────────────

MAX_TOOL_TURNS = 6           # Hard cap: prevents runaway loops + runaway costs
MAX_TOKENS_PER_CALL = 2048   # Output tokens per LLM call
WRITING_MODEL = "claude-sonnet-4-6"
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

# ── Secret redaction ──────────────────────────────────────────────────────

_SECRET_PATTERNS = re.compile(
    r"""(
        Bearer\s+[A-Za-z0-9\-_\.]+  |  # Bearer tokens
        sk-[A-Za-z0-9]+              |  # OpenAI keys
        AQE[A-Za-z0-9+/=]+          |  # LinkedIn cookies
        AIza[A-Za-z0-9\-_]+         |  # Google API keys
        EAA[A-Za-z0-9]+             |  # Facebook/Instagram tokens
        "password"\s*:\s*"[^"]+"    |  # JSON password fields
        "token"\s*:\s*"[^"]+"       |  # JSON token fields
        "key"\s*:\s*"[^"]+"            # JSON key fields
    )""",
    re.VERBOSE | re.IGNORECASE,
)


def _redact(text: str) -> str:
    """Replace secrets in text with [REDACTED] for safe ledger storage."""
    return _SECRET_PATTERNS.sub("[REDACTED]", text)


def _summarise(text: str, max_len: int = 300) -> str:
    """Truncate + redact text for ledger storage."""
    return _redact(str(text)[:max_len])


# ── Tool definitions (Anthropic format) ──────────────────────────────────

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information, recent trends, news, and research. "
            "Uses Perplexity sonar-pro for real-time results with source citations. "
            "Use this for: competitor research, trend analysis, industry news, statistics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Specific search query. Be precise — not vague.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "synthesize_research",
        "description": (
            "Synthesize multiple pieces of research data into a structured analysis. "
            "Uses Gemini 2.0 Flash for large-context synthesis. "
            "Use this after gathering multiple search results to combine into insights."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "research_text": {
                    "type": "string",
                    "description": "The collected research data to synthesize.",
                },
                "synthesis_goal": {
                    "type": "string",
                    "description": "What to extract or conclude from the research.",
                },
            },
            "required": ["research_text", "synthesis_goal"],
        },
    },
    {
        "name": "fetch_brand_profile",
        "description": (
            "Fetch the brand profile (positioning, voice, ICA, offer) from the database. "
            "Use this to ground your output in the user's specific brand context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "brand_id": {
                    "type": "string",
                    "description": "The UUID of the brand to fetch.",
                }
            },
            "required": ["brand_id"],
        },
    },
    {
        "name": "read_playbook",
        "description": (
            "Read this agent's playbook — the SOPs and rules that govern how it should work. "
            "Call this at the start of a task to load your current instructions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The agent ID whose playbook to load (e.g. 'copywriter').",
                },
                "user_id": {
                    "type": "string",
                    "description": "The user ID (for user-specific playbook overrides).",
                },
            },
            "required": ["agent_id", "user_id"],
        },
    },
    {
        "name": "score_content_quality",
        "description": (
            "Run a fast rule-based quality check on a piece of content. "
            "Returns scores for: length, hook_present, no_ai_tells, no_em_dashes. "
            "Use before delivering final output to self-check."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content text to evaluate.",
                }
            },
            "required": ["content"],
        },
    },
    {
        "name": "read_agent_training_docs",
        "description": (
            "Load training materials uploaded by the user for this specific agent "
            "(PDFs, frameworks, books, SOPs). Always call this at the start of a task "
            "to ground your work in user-provided methodology. "
            "Returns formatted markdown chunks from the knowledge base."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The agent ID to load training docs for (e.g. 'brand-researcher', 'account-manager').",
                },
                "user_id": {
                    "type": "string",
                    "description": "The user ID (to load user-specific training documents).",
                },
            },
            "required": ["agent_id", "user_id"],
        },
    },
    {
        "name": "generate_image",
        "description": (
            "Generate a photorealistic image from plain English. "
            "Claude Haiku first structures the prompt with camera specs (lens, aperture), "
            "lighting (named setup, direction), composition, color grading (film stock reference), "
            "and negative constraints — raising the usable generation rate from ~68% to ~92%. "
            "Then calls Nano Banana 2 via Higgsfield (or Gemini as fallback). "
            "Returns an image URL and the structured prompt used. "
            "Use for: post visuals, ad creatives, brand imagery, LinkedIn headers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Plain English description of the image to generate.",
                },
                "style": {
                    "type": "string",
                    "enum": ["photorealistic", "cinematic", "branded", "editorial", "lifestyle"],
                    "description": "Visual style. Default: photorealistic.",
                },
                "format": {
                    "type": "string",
                    "enum": ["square", "landscape", "portrait", "story"],
                    "description": "Aspect ratio: square (1:1 LinkedIn/Instagram), landscape (16:9 YouTube), portrait (4:5 feed), story (9:16 Stories).",
                },
            },
            "required": ["description"],
        },
    },
]


# ── Tool executors ────────────────────────────────────────────────────────


def _exec_web_search(query: str) -> str:
    """Call Perplexity sonar-pro for real-time web search with citations."""
    if not settings.perplexity_api_key:
        # Fall back to Tavily if Perplexity key not set
        return _exec_web_search_tavily(query)

    # Sanitise: strip HTML-like chars, cap length (injection prevention)
    safe_query = re.sub(r"[<>\"';&]", "", query).strip()[:200]

    try:
        resp = httpx.post(
            PERPLEXITY_URL,
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": safe_query}],
                "max_tokens": 1024,
            },
            headers={
                "Authorization": f"Bearer {settings.perplexity_api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        if citations:
            content += "\n\nSources:\n" + "\n".join(f"- {c}" for c in citations[:5])
        return content
    except Exception as exc:
        logger.warning("Perplexity search failed for %r: %s — trying Tavily fallback", query, exc)
        return _exec_web_search_tavily(query)


def _exec_web_search_tavily(query: str) -> str:
    """Tavily fallback for web search when Perplexity is unavailable."""
    if not settings.tavily_api_key:
        return f"[web_search unavailable — no search API key configured for query: {query!r}]"

    safe_query = re.sub(r"[<>\"';&]", "", query).strip()[:200]
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": settings.tavily_api_key, "query": safe_query, "max_results": 5},
            timeout=12.0,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return f"No results found for: {safe_query!r}"
        lines = [f"- {r.get('title', '')}: {r.get('content', '')[:300]}" for r in results]
        return "\n".join(lines)
    except Exception as exc:
        return f"[web_search error: {exc}]"


def _exec_synthesize_research(research_text: str, synthesis_goal: str) -> str:
    """Call Gemini 2.0 Flash for large-context research synthesis."""
    if not settings.gemini_api_key:
        # Graceful degradation: return a note without blocking the agent
        return f"[Gemini synthesis unavailable — GEMINI_API_KEY not set. Raw data: {research_text[:500]}]"

    prompt = (
        f"Goal: {synthesis_goal}\n\n"
        f"Research data to synthesize:\n{research_text[:15000]}\n\n"
        "Provide a structured synthesis with: key findings, patterns, "
        "actionable insights, and evidence. Be specific and concise."
    )
    try:
        resp = httpx.post(
            GEMINI_URL,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            params={"key": settings.gemini_api_key},
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        logger.warning("Gemini synthesis failed: %s", exc)
        return f"[Gemini synthesis error: {exc}. Raw data preserved.]"


def _exec_fetch_brand_profile(brand_id: str) -> str:
    """Fetch brand profile from Supabase."""
    try:
        sb = get_admin_client()
        result = (
            sb.table("personal_brands")
            .select("name, description, profile_json, is_client_brand")
            .eq("id", brand_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return f"[Brand {brand_id!r} not found]"
        row = result.data[0]
        profile = row.get("profile_json") or {}
        is_client = row.get("is_client_brand", False)
        summary: dict = {
            "name": row.get("name", ""),
            "description": row.get("description", ""),
            "positioning": profile.get("positioning", ""),
            "voice": profile.get("voice", ""),
            "ica": profile.get("ica", ""),
            "offer": profile.get("offer", ""),
            "content_pillars": profile.get("content_pillars", []),
            "voice_adjectives": profile.get("voice_adjectives", []),
        }
        # For client brands inject emotional journals + anxiety/benefit lists
        # so copywriter, landing page, and ad creative agents can write hyper-targeted copy
        if is_client:
            summary["is_client_brand"] = True
            summary["ica_summary"] = profile.get("ica_summary", "")
            summary["emotional_pain_journal"] = profile.get("emotional_pain_journal", "")
            summary["emotional_win_journal"] = profile.get("emotional_win_journal", "")
            summary["anxiety_list"] = profile.get("anxiety_list", [])
            summary["benefit_list"] = profile.get("benefit_list", [])
            summary["hormozi"] = profile.get("hormozi", {})
            summary["competitor_gap"] = profile.get("competitor_gap", "")
            summary["first_week_angles"] = profile.get("first_week_angles", [])
        return json.dumps(summary, ensure_ascii=False)
    except Exception as exc:
        logger.warning("fetch_brand_profile failed for %s: %s", brand_id, exc)
        return f"[Brand profile fetch error: {exc}]"


def _exec_read_playbook(agent_id: str, user_id: str) -> str:
    """Fetch this agent's playbook from Supabase."""
    try:
        sb = get_admin_client()
        result = (
            sb.table("agent_playbooks")
            .select("playbook_md, version")
            .eq("agent_id", agent_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return f"[No playbook found for agent {agent_id!r} — use default behaviour]"
        row = result.data[0]
        v = row.get("version", 1)
        md = row.get("playbook_md", "")
        return f"# Playbook v{v} for {agent_id}\n\n{md}" if md else "[Playbook is empty — use default behaviour]"
    except Exception as exc:
        logger.warning("read_playbook failed (%s / %s): %s", agent_id, user_id, exc)
        return f"[Playbook read error: {exc}]"


_AI_TELLS = [
    "it's worth noting", "it is worth noting", "as an ai", "i cannot",
    "i'm unable", "importantly,", "in conclusion,", "to summarize,",
    "firstly,", "secondly,", "thirdly,", "in today's", "delve into",
    "dive deep", "leverage", "synergy", "paradigm", "utilize",
]

_EM_DASHES = ["—", "–"]


def _exec_score_content_quality(content: str) -> str:
    """Fast rule-based quality scoring — no LLM call."""
    text = content.strip()
    word_count = len(text.split())
    char_count = len(text)

    # Hook present: first sentence ends with "?" or is <= 15 words
    first_sentence = text.split(".")[0].split("?")[0].split("!")[0]
    hook_present = len(first_sentence.split()) <= 15 or "?" in text[:100]

    # AI tells check
    lower = text.lower()
    found_ai_tells = [t for t in _AI_TELLS if t in lower]

    # Em dash check
    found_em_dashes = [d for d in _EM_DASHES if d in text]

    # Readability: avg sentence length
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
    avg_sentence_len = (sum(len(s.split()) for s in sentences) / len(sentences)) if sentences else 0

    scores = {
        "word_count": word_count,
        "hook_present": hook_present,
        "avg_sentence_length": round(avg_sentence_len, 1),
        "ai_tells_found": found_ai_tells,
        "em_dashes_found": found_em_dashes,
        "pass": len(found_ai_tells) == 0 and not found_em_dashes and hook_present,
        "issues": [],
    }
    if not hook_present:
        scores["issues"].append("Weak or missing hook in opening")
    if found_ai_tells:
        scores["issues"].append(f"AI-tell phrases found: {found_ai_tells}")
    if found_em_dashes:
        scores["issues"].append("Em dashes found — remove them")
    if avg_sentence_len > 20:
        scores["issues"].append(f"Sentences too long (avg {avg_sentence_len:.0f} words)")

    return json.dumps(scores)


def _exec_read_agent_training_docs(agent_id: str, user_id: str) -> str:
    """Fetch training documents for an agent from knowledge_documents table."""
    try:
        sb = get_admin_client()
        result = (
            sb.table("knowledge_documents")
            .select("title, content, doc_type, created_at")
            .eq("user_id", user_id)
            .contains("agent_scope", [agent_id])
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        if not result.data:
            return f"[No training documents found for agent {agent_id!r}. Using default methodology.]"
        chunks = []
        for doc in result.data:
            title = doc.get("title", "Untitled")
            content = (doc.get("content") or "")[:2000]
            dtype = doc.get("doc_type", "doc")
            chunks.append(f"## {title} ({dtype})\n\n{content}")
        return f"# Training Materials for {agent_id}\n\n" + "\n\n---\n\n".join(chunks)
    except Exception as exc:
        logger.warning("read_agent_training_docs failed (%s / %s): %s", agent_id, user_id, exc)
        return f"[Training docs error: {exc} — proceeding with default methodology]"


def _exec_generate_image(description: str, style: str = "photorealistic", img_format: str = "square") -> str:
    """Generate an image via Nano Banana 2 (Higgsfield/Gemini). Returns JSON {url, prompt}."""
    try:
        from app.services.image_gen import generate_image as _gen
        result = _gen(
            description=description,
            style=style,
            img_format=img_format,
        )
        return json.dumps({
            "url": result.get("url"),
            "model_used": result.get("model_used"),
            "prompt": result.get("structured_prompt", "")[:300],
            "error": result.get("error"),
        })
    except Exception as exc:
        logger.warning("generate_image tool failed: %s", exc)
        return json.dumps({"url": None, "error": str(exc)})


# ── Tool dispatcher ───────────────────────────────────────────────────────


def _dispatch_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Execute a tool call by name and return the result as a string."""
    if tool_name == "web_search":
        return _exec_web_search(tool_input.get("query", ""))
    if tool_name == "synthesize_research":
        return _exec_synthesize_research(
            tool_input.get("research_text", ""),
            tool_input.get("synthesis_goal", ""),
        )
    if tool_name == "fetch_brand_profile":
        return _exec_fetch_brand_profile(tool_input.get("brand_id", ""))
    if tool_name == "read_playbook":
        return _exec_read_playbook(
            tool_input.get("agent_id", ""),
            tool_input.get("user_id", ""),
        )
    if tool_name == "score_content_quality":
        return _exec_score_content_quality(tool_input.get("content", ""))
    if tool_name == "read_agent_training_docs":
        return _exec_read_agent_training_docs(
            tool_input.get("agent_id", ""),
            tool_input.get("user_id", ""),
        )
    if tool_name == "generate_image":
        return _exec_generate_image(
            description=tool_input.get("description", ""),
            style=tool_input.get("style", "photorealistic"),
            img_format=tool_input.get("format", "square"),
        )
    return f"[Unknown tool: {tool_name!r}]"


# ── Ledger helpers ────────────────────────────────────────────────────────


def _write_ledger_entry(
    *,
    user_id: str,
    run_id: str,
    agent_id: str,
    action_type: str,
    action_description: str,
    tool_name: Optional[str] = None,
    tool_input_summary: Optional[str] = None,
    tool_result_summary: Optional[str] = None,
    tokens_used: int = 0,
) -> None:
    """Write one ledger entry. Wrapped in try/except — never blocks the main task."""
    try:
        sb = get_admin_client()
        sb.table("agent_ledger").insert({
            "user_id": user_id,
            "run_id": run_id,
            "agent_id": agent_id,
            "action_type": action_type,
            "action_description": action_description,
            "tool_name": tool_name,
            "tool_input_summary": tool_input_summary,
            "tool_result_summary": tool_result_summary,
            "tokens_used": tokens_used,
        }).execute()
    except Exception as exc:
        logger.warning("Ledger write failed (run=%s, agent=%s): %s", run_id, agent_id, exc)


def _write_run_record(
    *,
    run_id: str,
    user_id: str,
    agent_id: str,
    task_type: str,
    status: str,
    prompt_summary: str = "",
    result_summary: str = "",
    error_text: str = "",
    model_used: str = "",
    total_tokens: int = 0,
    tool_calls_count: int = 0,
    duration_ms: int = 0,
    brand_id: Optional[str] = None,
) -> None:
    """Upsert an sdk_agent_runs record (insert on start, update on finish)."""
    try:
        sb = get_admin_client()
        sb.table("sdk_agent_runs").upsert({
            "id": run_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "task_type": task_type,
            "status": status,
            "prompt_summary": _summarise(prompt_summary, 200),
            "result_summary": _summarise(result_summary, 300),
            "error_text": error_text[:500] if error_text else None,
            "model_used": model_used,
            "total_tokens": total_tokens,
            "tool_calls_count": tool_calls_count,
            "duration_ms": duration_ms,
            "brand_id": brand_id,
            "completed_at": None if status == "running" else "now()",
        }).execute()
    except Exception as exc:
        logger.warning("Run record write failed (run=%s): %s", run_id, exc)


# ── Core agent loop ───────────────────────────────────────────────────────


def run_tool_use_agent(
    *,
    agent_id: str,
    task_type: str,
    system_prompt: str,
    user_prompt: str,
    user_id: str,
    brand_id: Optional[str] = None,
    available_tools: Optional[List[str]] = None,
    model: str = WRITING_MODEL,
    temperature: float = 0.7,
) -> AgentResult:
    """Run a multi-step tool-use agent using the Anthropic Messages API.

    Args:
        agent_id: Which agent is running (e.g. "copywriter", "research").
        task_type: Short task label for ledger (e.g. "ad_creative", "brand_research").
        system_prompt: Base system instructions for the agent.
        user_prompt: The specific task request.
        user_id: Supabase user ID (for playbook lookup + ledger ownership).
        brand_id: Optional brand UUID (for fetch_brand_profile tool).
        available_tools: Subset of TOOL_DEFINITIONS to expose. None = all tools.
        model: Anthropic model to use. Defaults to WRITING_MODEL (claude-sonnet-4-6).
        temperature: LLM temperature.

    Returns:
        AgentResult with the final text in `content`.
    """
    if not settings.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set — tool-use agent cannot run")
        return AgentResult(
            success=False,
            content="",
            error="Anthropic API key not configured.",
        )

    run_id = str(uuid.uuid4())
    start_time = time.monotonic()
    total_tokens = 0
    tool_calls_count = 0

    # Filter tools to requested subset
    if available_tools is not None:
        tools = [t for t in TOOL_DEFINITIONS if t["name"] in available_tools]
    else:
        tools = TOOL_DEFINITIONS

    # Write initial run record
    _write_run_record(
        run_id=run_id,
        user_id=user_id,
        agent_id=agent_id,
        task_type=task_type,
        status="running",
        prompt_summary=user_prompt,
        model_used=model,
        brand_id=brand_id,
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    messages: List[Dict[str, Any]] = [{"role": "user", "content": user_prompt}]

    final_text = ""
    last_exc: Optional[Exception] = None

    try:
        for turn in range(MAX_TOOL_TURNS):
            resp = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS_PER_CALL,
                temperature=temperature,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )
            total_tokens += resp.usage.input_tokens + resp.usage.output_tokens

            # Extract text and tool use blocks
            text_blocks = [b for b in resp.content if b.type == "text"]
            tool_blocks = [b for b in resp.content if b.type == "tool_use"]

            # Append assistant message to history
            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "end_turn" or not tool_blocks:
                # Agent is done
                final_text = " ".join(b.text for b in text_blocks).strip()

                _write_ledger_entry(
                    user_id=user_id,
                    run_id=run_id,
                    agent_id=agent_id,
                    action_type="output",
                    action_description=f"Agent completed after {turn + 1} turn(s)",
                    tool_result_summary=_summarise(final_text),
                    tokens_used=total_tokens,
                )
                break

            # Execute each tool call
            tool_results = []
            for tool_block in tool_blocks:
                t_name = tool_block.name
                t_input = tool_block.input or {}
                tool_calls_count += 1

                _write_ledger_entry(
                    user_id=user_id,
                    run_id=run_id,
                    agent_id=agent_id,
                    action_type="tool_call",
                    action_description=f"Called tool: {t_name}",
                    tool_name=t_name,
                    tool_input_summary=_summarise(json.dumps(t_input), 200),
                )

                result_text = _dispatch_tool(t_name, t_input)

                _write_ledger_entry(
                    user_id=user_id,
                    run_id=run_id,
                    agent_id=agent_id,
                    action_type="tool_call",
                    action_description=f"Tool result received: {t_name}",
                    tool_name=t_name,
                    tool_result_summary=_summarise(result_text),
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_text,
                })

            messages.append({"role": "user", "content": tool_results})

        else:
            # Loop exhausted without end_turn
            logger.warning(
                "Tool-use agent %s hit MAX_TOOL_TURNS=%d for task=%s",
                agent_id, MAX_TOOL_TURNS, task_type,
            )
            _write_ledger_entry(
                user_id=user_id,
                run_id=run_id,
                agent_id=agent_id,
                action_type="error",
                action_description=f"Max tool turns ({MAX_TOOL_TURNS}) exceeded",
            )
            duration_ms = int((time.monotonic() - start_time) * 1000)
            _write_run_record(
                run_id=run_id,
                user_id=user_id,
                agent_id=agent_id,
                task_type=task_type,
                status="failed",
                error_text=f"Max tool turns ({MAX_TOOL_TURNS}) exceeded",
                model_used=model,
                total_tokens=total_tokens,
                tool_calls_count=tool_calls_count,
                duration_ms=duration_ms,
                brand_id=brand_id,
            )
            return AgentResult(
                success=False,
                content="",
                error=f"Agent loop exceeded {MAX_TOOL_TURNS} tool turns without completing.",
                model_used=model,
                tokens_used=total_tokens,
            )

    except Exception as exc:
        last_exc = exc
        logger.error("Tool-use agent %s failed: %s", agent_id, exc, exc_info=True)
        duration_ms = int((time.monotonic() - start_time) * 1000)
        _write_run_record(
            run_id=run_id,
            user_id=user_id,
            agent_id=agent_id,
            task_type=task_type,
            status="failed",
            error_text=str(exc)[:500],
            model_used=model,
            total_tokens=total_tokens,
            tool_calls_count=tool_calls_count,
            duration_ms=duration_ms,
            brand_id=brand_id,
        )
        return AgentResult(
            success=False,
            content="",
            error=str(exc),
            model_used=model,
            tokens_used=total_tokens,
        )

    duration_ms = int((time.monotonic() - start_time) * 1000)
    _write_run_record(
        run_id=run_id,
        user_id=user_id,
        agent_id=agent_id,
        task_type=task_type,
        status="completed",
        prompt_summary=user_prompt,
        result_summary=final_text,
        model_used=model,
        total_tokens=total_tokens,
        tool_calls_count=tool_calls_count,
        duration_ms=duration_ms,
        brand_id=brand_id,
    )

    return AgentResult(
        success=True,
        content=final_text,
        model_used=model,
        tokens_used=total_tokens,
    )
