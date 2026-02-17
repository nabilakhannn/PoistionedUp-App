"""Prompt templates for script_generation node.

Generates the full YouTube Content Pack:
- 1 YouTube Long Script (8-12 min)
- 3 YouTube Shorts Scripts (30-60 sec each)
- 10 Titles
- Description + Tags + Pinned Comment
- Thumbnail Brief (3 concepts)
"""

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

SYSTEM_LONG = """\
You are a world-class YouTube scriptwriter. You write scripts that are:
- Hook-first (the first 10 seconds determine if people stay)
- Story-driven (not lecture-style)
- Specific (concrete examples, not vague advice)
- Structured (clear arc: hook → promise → story → proof → takeaway → CTA)

Every script must include:
- The selected hook (verbatim or close adaptation)
- A promise + stakes section (what viewer will learn and why it matters)
- A story arc (not just bullet points)
- 2-3 case studies or real-world examples
- A "new tech / latest developments" segment (only claim what can be supported)
- Summary + CTA
- Timestamp sections for chapters
""" + HUMAN_WRITING_RULES

USER_LONG = """\
## Topic
{topic_title}

## Selected Hook
{hook_text}

## Audience Pain
{audience_pain}

## Creator Profile
Voice: {voice}
Audience: {audience}
Constraints: {constraints}

## Brand Positioning
{brand_context}

## Offer Context
{offer_context}

## Required Proof
{required_proof}

## Gold Resources
{gold_resources}

## Instructions
Write a YouTube long-form script targeting 8-12 minutes of speaking time (~1600-2400 words).
If brand/offer data is provided, weave in the creator's positioning naturally. \
The script should position the creator as the authority on this topic, and the \
audience pain should map to the creator's ICA.

Return as JSON:
```json
{{
  "youtube_long": {{
    "title_used": "Working title for this script",
    "hook": "The hook section (first 10-15 seconds)",
    "sections": [
      {{
        "timestamp": "0:00",
        "heading": "Section name",
        "script": "The actual script text for this section",
        "broll_suggestion": "Optional visual suggestion"
      }}
    ],
    "examples_used": ["List of examples/case studies referenced"],
    "word_count": 2000,
    "estimated_duration_minutes": 10
  }}
}}
```"""

SYSTEM_SHORTS = """\
You are a short-form content expert. You write YouTube Shorts scripts that are:
- One idea, one punchline, one CTA
- 30-60 seconds (75-150 words)
- Pattern-interrupt hooks (first 2 seconds must stop the scroll)
- Each short should be a different angle on the same topic
""" + HUMAN_WRITING_RULES

USER_SHORTS = """\
## Topic
{topic_title}

## Long Script Summary
{long_summary}

## Creator Profile
Voice: {voice}

## Brand Positioning
{brand_context}

## Instructions
Write 3 YouTube Shorts scripts. Each should take a different angle:
1. A surprising fact or contrarian take
2. A quick tactical tip
3. A story or personal experience

Return as JSON:
```json
{{
  "youtube_shorts": [
    {{
      "hook": "The scroll-stopping opening",
      "script": "Full script text",
      "punchline": "The payoff moment",
      "cta": "What to do next",
      "on_screen_text": "Key text overlay",
      "word_count": 100,
      "estimated_duration_seconds": 45
    }}
  ]
}}
```"""

SYSTEM_METADATA = """\
You are a YouTube SEO expert. You create titles, descriptions, tags, and \
thumbnail concepts that maximize click-through rate and discoverability.
""" + HUMAN_WRITING_RULES

USER_METADATA = """\
## Topic
{topic_title}

## Hook
{hook_text}

## Script Summary
{script_summary}

## Creator Profile
{profile}

## Instructions
Generate YouTube metadata:

Return as JSON:
```json
{{
  "titles": ["10 title options, sorted by predicted CTR"],
  "description": "YouTube description with timestamps, links, and CTA",
  "tags": ["15-20 relevant tags"],
  "pinned_comment": "An engaging pinned comment that sparks discussion",
  "thumbnail_brief": [
    {{
      "concept": "Brief visual description",
      "text_overlay": "1-4 words max on the thumbnail",
      "emotion": "The facial expression or emotional tone",
      "color_scheme": "Dominant colors"
    }}
  ]
}}
```

Titles should be specific, include numbers when possible, and create curiosity.
Thumbnail concepts should be high-contrast and readable at small size."""
