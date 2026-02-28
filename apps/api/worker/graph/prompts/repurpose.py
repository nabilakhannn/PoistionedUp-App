"""Prompt templates for content repurposing across platforms.

Takes a single piece of source content and adapts it for a specific
target platform while preserving the core message and brand voice.
"""

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

SYSTEM = """\
You are a multi-platform content adaptation expert. You take one piece \
of content and transform it for a specific platform while keeping the \
core message, brand voice, and value intact.

Your repurposing rules:
- Adapt the FORMAT, not just the length. Each platform has its own rhythm.
- Keep the core insight or value proposition. Do not water it down.
- Match the native tone of the target platform. LinkedIn is not Twitter.
- Respect character limits and formatting norms strictly.
- Add platform-specific elements (hashtags for Instagram, thread hooks for Twitter).
- Do not just shorten. Restructure around what works on the target platform.
- The repurposed version should stand alone. Someone who never saw the original \
should still get full value.

""" + HUMAN_WRITING_RULES

# Per-platform constraints injected into the user prompt
PLATFORM_CONSTRAINTS = {
    "linkedin": {
        "content_type": "linkedin_post",
        "char_limit": 3000,
        "rules": (
            "Professional but human tone. Short paragraphs with line breaks. "
            "Hook in the first line (before the 'see more' fold). "
            "Under 3000 characters. End with a question or soft CTA. "
            "No emoji bullets unless the source had them."
        ),
    },
    "twitter": {
        "content_type": "twitter_post",
        "char_limit": 280,
        "rules": (
            "Punchy, under 280 characters for a single tweet. "
            "If the content needs more space, create a thread (max 5 tweets). "
            "For threads: number each tweet, first tweet is the hook, "
            "last tweet is the CTA. Each tweet should stand alone but flow together."
        ),
    },
    "instagram": {
        "content_type": "instagram_caption",
        "char_limit": 2200,
        "rules": (
            "Visual-first caption. Start with a hook line. "
            "Use line breaks for readability. Emojis are acceptable sparingly. "
            "Add a hashtag block at the end (8-15 relevant hashtags). "
            "Under 2200 characters. End with a CTA (save, share, comment)."
        ),
    },
    "tiktok": {
        "content_type": "tiktok_script",
        "char_limit": None,
        "rules": (
            "Spoken script format for a 30-60 second video. "
            "Hook in the first 3 seconds, pattern interrupt or bold claim. "
            "Conversational, like talking to a friend. 80-150 words. "
            "End with a strong CTA or cliffhanger. "
            "Include [visual direction] cues in brackets."
        ),
    },
    "facebook": {
        "content_type": "facebook_post",
        "char_limit": 5000,
        "rules": (
            "Conversational, medium-length. "
            "Ask a question to drive comments. "
            "Can be longer than LinkedIn but still needs a hook. "
            "Personal stories work well. Under 500 words."
        ),
    },
    "ad_copy": {
        "content_type": "ad_copy",
        "char_limit": 125,
        "rules": (
            "Direct response ad format. Lead with the benefit or pain point. "
            "Headline: max 40 characters. Body: max 125 characters. "
            "Include a specific CTA. Add an audience_hint (who this targets). "
            "Write 2 variants: one for Facebook, one for Instagram."
        ),
    },
    "carousel": {
        "content_type": "carousel",
        "char_limit": None,
        "rules": (
            "Structured slide-by-slide format. 6-8 slides. "
            "Each slide: title (max 8 words), body (2-3 lines), visual_cue. "
            "Cover slide: bold statement or question. "
            "Last slide: CTA. One idea per slide."
        ),
    },
    "email": {
        "content_type": "email_snippet",
        "char_limit": None,
        "rules": (
            "Newsletter-friendly format. "
            "Subject line: max 60 characters, curiosity-driven. "
            "Body: 150-300 words. Personal tone, one clear takeaway. "
            "End with a single CTA link or question."
        ),
    },
    "blog": {
        "content_type": "blog_intro",
        "char_limit": None,
        "rules": (
            "SEO-friendly blog introduction. 150-250 words. "
            "Include the main keyword naturally in the first paragraph. "
            "Hook the reader, state the problem, preview the solution. "
            "Use a conversational but authoritative tone."
        ),
    },
}

USER = """\
## Source Content
Platform: {source_platform}

{source_content}

## Target Platform: {target_platform}

## Platform Rules
{platform_rules}

## Creator Profile
Voice: {voice}

## Brand Positioning
{brand_context}

## Instructions
Repurpose the source content above for {target_platform}. Follow the platform \
rules strictly. The repurposed version should stand alone and deliver full value \
to someone who never saw the original.

Return as JSON:
```json
{{
  "title": "A short title for this repurposed piece",
  "body": "The full repurposed content",
  "content_type": "{content_type}",
  "platform": "{target_platform}",
  "metadata": {{
    "char_count": 0,
    "hashtags": [],
    "cta": ""
  }}
}}
```"""
