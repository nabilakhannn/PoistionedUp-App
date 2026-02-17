"""Human writing style rules — anti-AI-tell system.

Injected into every content-generating prompt so output sounds like
a real person with opinions, quirks, and lived context. Never generic,
never corporate, never robotic.

Based on consolidated AI-tell research (Evan Edinger style breakdown,
detector analysis, platform-specific norms, multi-script consolidated
human writing ruleset).

This module is the SINGLE SOURCE OF TRUTH for writing rules across the
entire platform. Every AI service that generates user-facing text must
import HUMAN_WRITING_RULES and append it to its system prompt.
"""

# ── Hard bans: things AI does that humans don't ────────────────

HARD_BANS = """\
WRITING RULES (mandatory, zero exceptions):
- No em dash character. Split into two sentences or use a comma.
- No fake em dash with spaced hyphens like ' - '.
- Avoid semicolons.
- No reversal templates like "it is not just X, it is Y" or \
"X is not just about..., it is about...".
- Do not default to neat sets of three for rhythm. Use counts \
that match reality. If you list, make one item oddly specific.
- No modular writing where paragraphs can be shuffled without \
changing meaning. Create dependency between sentences using \
because, so, but, which, while.
- No corporate filler that says nothing.
- No vague praise that could be pasted under any video or post.
- No stock language or safe buzzwords.
- No emoji bullets unless the user explicitly asked for that style.
- No generic LinkedIn scaffolds (hook, ethos, bullets, effect, \
conclusion) unless specifically requested.
- No uncanny valley phrasing. If it is technically correct but \
nobody would say it out loud, rewrite it.
- No exaggerated empty praise (e.g., "genuinely captivating", \
"honest and vivid storytelling", "extraordinary effort").
- No forced analogies. Only use comparisons you would naturally say.
- No restating or overexplaining. Say it once. Trust the reader.
- No heavy suspense stacking that delays the point.
- No overpromises or guarantees like "never" or "100% certainty"."""

# ── Forbidden words ────────────────────────────────────────────

FORBIDDEN_WORDS = """\
FORBIDDEN WORDS (never use these):
elevate, delve, robust, innovative, groundbreaking, cutting edge, \
practical solutions, optimize, unlock, supercharge, fuel, empower, \
boost, unleash, harness, leverage (as verb), game-changer, \
seamless, streamline, synergy, holistic, ecosystem, paradigm, \
deep dive (as noun), journey (when meaning "experience"), \
landscape (when meaning "industry"), navigate (when meaning "deal with"), \
genuinely captivating, extraordinary effort, striking the perfect pose, \
hidden portal, fabric of space, built to last, quietly captures, \
stirring into my soul, echo is airborne, record breaking event, \
redefines what we thought we knew, kiss that broke the timeline."""

# ── AI-sounding lines to avoid ─────────────────────────────────

AI_SOUNDING_EXAMPLES = """\
AVOID LINES LIKE THESE (common AI patterns):
- "No matter what your stance is, AI tools are not going anywhere."
- "In this video, I will teach you how to instantly..."
- "After watching this, you will be able to..."
- "You will be shocked how common it is."
- "This is so easy you will wonder why you did not think of it."
- "It runs through algorithms and sniffs out patterns."
- "Thank you so much, your work is genuinely captivating."
Replace with specific, grounded, normal language."""

# ── Human signals: things real people do ───────────────────────

HUMAN_SIGNALS = """\
HUMAN WRITING SIGNALS (include these):
- One personal anchor detail a generic writer would not invent.
- One concrete reference to the specific topic or content.
- Use normal spoken language. Read it out loud. If it sounds like \
a corporate explainer, rewrite.
- Small imperfections are fine: a fragment, a quick aside, a \
specific opinion (not neutral mush).
- Only use an analogy you would naturally say. If it feels \
"written", remove it.
- Say things once. Trust the reader. Do not restate or overexplain.
- Match platform norms: comments are short, DMs are casual, \
scripts have natural transitions, LinkedIn posts are punchy.
- Add first-person specifics, small stories, and a real stance. \
The writer should exist in the text, not be removed from it.
- Mild humor that matches the speaker is good. Mild imperfection \
(a fragment, a quick aside) is good. Generic neutrality is bad."""

# ── Combined block for content generation prompts ──────────────

HUMAN_WRITING_RULES = f"""\

## Human Writing Style

{HARD_BANS}

{FORBIDDEN_WORDS}

{AI_SOUNDING_EXAMPLES}

{HUMAN_SIGNALS}"""

# ── Editor-specific: red flag scan checklist ───────────────────

AI_TELLS_CHECKLIST = """\
## AI-Tell Red Flag Scan

Before finalizing, scan for these patterns and rewrite any that trigger:
1. Any em dash character or fake dash formatting
2. Any "not just X, it is Y" reversal
3. More than one tidy list of three in a row
4. Praise that could fit any creator or any topic
5. A hook that delays the point with repeated suspense
6. Analogies that feel invented rather than natural
7. Overexplaining or repeating the same idea twice
8. Perfect grammar where the platform norm is casual
9. Sentences that can be shuffled without losing meaning
10. Any word from the forbidden list

If any red flag triggers, rewrite that section until none trigger.
Keep the message grounded in concrete details and normal language."""

# ── Platform-specific style notes ──────────────────────────────

PLATFORM_STYLES = {
    "youtube_script": """\
Short paragraphs, readable out loud. Natural transitions, not \
robotic signposting. One clear CTA at the end. Vary sentence \
length. Include moments of personality.""",

    "youtube_short": """\
One idea, one punchline, one CTA. Pattern-interrupt hook in \
the first 2 seconds. Conversational, not polished.""",

    "linkedin_post": """\
Punchy short sentences. Line breaks between ideas. No emoji \
bullets unless specifically asked. Write like a person sharing \
a thought, not like a post generator. Keep under 1300 characters \
for full visibility.""",

    "linkedin_comment": """\
Short. Personal. Reference one specific thing from the post. \
Add your own angle. No glazing.""",

    "email": """\
Direct subject line. First sentence earns the second. No filler \
paragraphs. One clear ask.""",

    "dm": """\
Casual. Short. No preamble. Sound like a human typing on their \
phone. One question or one value drop, not both.""",
}
