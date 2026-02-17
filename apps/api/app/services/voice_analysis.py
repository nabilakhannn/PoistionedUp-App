"""Voice DNA analysis service — extracts a creator's writing style profile.

Analyzes resource chunks from a collection to build a structured Voice DNA:
tone, sentence style, hooks, CTAs, signature phrases, and content structure.
"""

import json
import logging
import random
from typing import Any, Dict, List, Optional

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

logger = logging.getLogger(__name__)

# How many chunks to sample per collection for analysis
MAX_SAMPLE_CHUNKS = 60
# Minimum chunks needed for meaningful analysis
MIN_CHUNKS_FOR_ANALYSIS = 5

VOICE_DNA_SYSTEM = """You are a writing style analyst. You study content from a specific creator and extract their unique voice profile.

Analyze the provided content samples and extract a structured "Voice DNA" profile.

Return a JSON object with EXACTLY these fields:
{
  "tone": "One sentence describing their overall tone (e.g., 'Direct and aggressive with occasional humor')",
  "sentence_style": "Their sentence structure pattern (e.g., 'Short punchy sentences. Rarely more than 10 words. Uses fragments for emphasis.')",
  "vocabulary_level": "Their word choice style (e.g., 'Simple everyday language, avoids jargon, uses slang occasionally')",
  "hook_patterns": ["List of 3-5 hook types they use most", "e.g., 'Bold contrarian claims'", "'Rhetorical questions'"],
  "cta_patterns": ["List of 2-3 CTA styles they use", "e.g., 'Direct command with urgency'"],
  "signature_phrases": ["List of 5-10 phrases or expressions unique to this creator"],
  "content_structure": "How they typically structure content (e.g., 'Problem → agitate → solve → proof → CTA')",
  "personality_traits": ["List of 3-5 personality traits visible in their writing"],
  "sample_hooks": ["5-10 example hooks from their content, quoted exactly"]
}

Be specific and cite actual patterns from the content. Don't be generic.
If the content is too short or doesn't have clear patterns, say so honestly in each field.""" + HUMAN_WRITING_RULES


def _get_collection_chunks(admin, collection_id: str) -> List[Dict[str, Any]]:
    """Fetch all resource chunks belonging to a collection."""
    resp = (
        admin.table("resource_chunks")
        .select("chunk_text, metadata, resource_id")
        .in_(
            "resource_id",
            admin.table("resources")
            .select("id")
            .eq("collection_id", collection_id)
        )
        .execute()
    )
    return resp.data if resp.data else []


def _get_collection_chunks_via_join(admin, collection_id: str) -> List[Dict[str, Any]]:
    """Fetch chunks for a collection by querying resources first, then chunks.

    Two-step approach since Supabase PostgREST doesn't support subquery in .in_().
    """
    # Step 1: Get resource IDs in this collection
    res_resp = (
        admin.table("resources")
        .select("id")
        .eq("collection_id", collection_id)
        .execute()
    )
    if not res_resp.data:
        return []

    resource_ids = [r["id"] for r in res_resp.data]

    # Step 2: Fetch chunks for those resources
    chunks_resp = (
        admin.table("resource_chunks")
        .select("chunk_text, metadata, resource_id")
        .in_("resource_id", resource_ids)
        .execute()
    )
    return chunks_resp.data if chunks_resp.data else []


def _sample_chunks(chunks: List[Dict[str, Any]], max_samples: int = MAX_SAMPLE_CHUNKS) -> List[Dict[str, Any]]:
    """Sample diverse chunks from a collection.

    Strategy: take chunks from different resources, prefer early chunks
    (which often contain hooks/intros) and middle chunks (body style).
    """
    if len(chunks) <= max_samples:
        return chunks

    # Group by resource_id
    by_resource: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in chunks:
        rid = chunk.get("resource_id", "unknown")
        by_resource.setdefault(rid, []).append(chunk)

    sampled = []
    per_resource = max(1, max_samples // len(by_resource))

    for rid, resource_chunks in by_resource.items():
        if len(resource_chunks) <= per_resource:
            sampled.extend(resource_chunks)
        else:
            # Take first chunk (hook/intro), last chunk (CTA/conclusion), and random middles
            selected = [resource_chunks[0]]
            if len(resource_chunks) > 1:
                selected.append(resource_chunks[-1])
            remaining = resource_chunks[1:-1] if len(resource_chunks) > 2 else []
            if remaining and per_resource > 2:
                selected.extend(random.sample(remaining, min(per_resource - 2, len(remaining))))
            sampled.extend(selected)

    # If still over limit, random sample
    if len(sampled) > max_samples:
        sampled = random.sample(sampled, max_samples)

    return sampled


def _build_analysis_prompt(chunks: List[Dict[str, Any]], collection_name: str) -> str:
    """Build the user prompt with sampled content for Voice DNA extraction."""
    content_parts = []
    for i, chunk in enumerate(chunks):
        text = chunk.get("chunk_text", "").strip()
        if text:
            content_parts.append(f"[Sample {i + 1}]\n{text}")

    content_block = "\n\n---\n\n".join(content_parts)

    return (
        f"Analyze the following content samples from the creator/source: \"{collection_name}\"\n\n"
        f"There are {len(chunks)} content samples below.\n\n"
        f"{content_block}\n\n"
        f"Extract the Voice DNA profile as JSON."
    )


def analyze_voice_dna(
    admin,
    collection_id: str,
    collection_name: str,
) -> Dict[str, Any]:
    """Analyze a collection's content and extract Voice DNA.

    Returns a dict matching the VoiceDNA schema fields plus analysis_chunk_count.
    Raises ValueError if not enough content.
    """
    # Fetch all chunks
    chunks = _get_collection_chunks_via_join(admin, collection_id)

    if len(chunks) < MIN_CHUNKS_FOR_ANALYSIS:
        raise ValueError(
            f"Not enough content for voice analysis. "
            f"Found {len(chunks)} chunks, need at least {MIN_CHUNKS_FOR_ANALYSIS}. "
            f"Add more resources to this collection first."
        )

    # Sample diverse chunks
    sampled = _sample_chunks(chunks)

    # Build prompt
    user_prompt = _build_analysis_prompt(sampled, collection_name)

    # Call LLM
    from worker.graph.llm import get_llm_client
    llm = get_llm_client()

    response = llm.chat(
        messages=[
            {"role": "system", "content": VOICE_DNA_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        model="gpt-4o",
        temperature=0.4,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    # Parse response
    from worker.graph.llm import parse_json_response
    result = parse_json_response(response["content"])

    # Ensure all expected fields exist with defaults
    voice_dna = {
        "tone": result.get("tone", ""),
        "sentence_style": result.get("sentence_style", ""),
        "vocabulary_level": result.get("vocabulary_level", ""),
        "hook_patterns": result.get("hook_patterns", []),
        "cta_patterns": result.get("cta_patterns", []),
        "signature_phrases": result.get("signature_phrases", []),
        "content_structure": result.get("content_structure", ""),
        "personality_traits": result.get("personality_traits", []),
        "sample_hooks": result.get("sample_hooks", []),
        "analysis_chunk_count": len(sampled),
    }

    # Store in collection
    admin.table("collections").update({
        "voice_dna": voice_dna,
    }).eq("id", collection_id).execute()

    logger.info(
        "Voice DNA extracted for collection '%s' (%s) from %d chunks",
        collection_name, collection_id, len(sampled),
    )

    return voice_dna


def format_voice_dna_instructions(voice_dna: Dict[str, Any]) -> str:
    """Format Voice DNA as system prompt instructions for content generation.

    Returns a string that can be appended to any LLM system prompt to
    instruct it to write in this creator's style.
    """
    if not voice_dna or not voice_dna.get("tone"):
        return ""

    parts = [
        "--- CREATOR VOICE STYLE INSTRUCTIONS ---",
        "Write content that matches this creator's distinctive voice:",
        "",
    ]

    if voice_dna.get("tone"):
        parts.append(f"TONE: {voice_dna['tone']}")

    if voice_dna.get("sentence_style"):
        parts.append(f"SENTENCE STYLE: {voice_dna['sentence_style']}")

    if voice_dna.get("vocabulary_level"):
        parts.append(f"VOCABULARY: {voice_dna['vocabulary_level']}")

    if voice_dna.get("content_structure"):
        parts.append(f"STRUCTURE: {voice_dna['content_structure']}")

    if voice_dna.get("hook_patterns"):
        parts.append(f"HOOK PATTERNS: {', '.join(voice_dna['hook_patterns'])}")

    if voice_dna.get("cta_patterns"):
        parts.append(f"CTA PATTERNS: {', '.join(voice_dna['cta_patterns'])}")

    if voice_dna.get("signature_phrases"):
        phrases = voice_dna["signature_phrases"][:10]
        parts.append(f"SIGNATURE PHRASES (use naturally): {', '.join(phrases)}")

    if voice_dna.get("personality_traits"):
        parts.append(f"PERSONALITY: {', '.join(voice_dna['personality_traits'])}")

    if voice_dna.get("sample_hooks"):
        parts.append("")
        parts.append("EXAMPLE HOOKS FROM THIS CREATOR (match this style):")
        for hook in voice_dna["sample_hooks"][:5]:
            parts.append(f"  - {hook}")

    parts.append("")
    parts.append(
        "IMPORTANT: Use the user's own message and brand context, "
        "but deliver it in THIS creator's voice and style patterns."
    )

    return "\n".join(parts)
