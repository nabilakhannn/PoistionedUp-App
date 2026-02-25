"""Brand Fields Registry: Defines all fields across the 8 brand modules.

Each field has metadata for smart sequencing: base weight, dependencies,
and the module it belongs to. This is the single source of truth for
what constitutes a complete Brand DNA.

Reference: PositionedUp System Prompt v2
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class BrandField:
    """A single field in the brand profile."""

    module: str
    key: str
    label: str
    question: str  # The coaching question to ask
    base_weight: int  # Higher = more foundational (1-10)
    dependencies: Tuple[str, ...] = ()  # Fields that should be filled first
    is_required: bool = True  # Required for brand completeness


# ── Module 1: Foundation ──────────────────────────────────────

FOUNDATION_FIELDS = [
    BrandField(
        module="foundation",
        key="what_you_do",
        label="What You Do",
        question=(
            "What do you do for a living? Not your job title. What do you "
            "actually DO for people? What problem do you solve? Who do you "
            "solve it for?"
        ),
        base_weight=10,  # Highest priority, everything depends on this
    ),
    BrandField(
        module="foundation",
        key="online_presence_status",
        label="Online Presence Status",
        question=(
            "Where are you right now with your online presence? Nothing at all, "
            "inactive profiles, occasional posting, active but no traction, or "
            "decent following but no revenue?"
        ),
        base_weight=8,
        dependencies=("foundation.what_you_do",),
    ),
    BrandField(
        module="foundation",
        key="90_day_goal",
        label="90-Day Goal",
        question=(
            "What is your goal? Why are you here? What does success look like "
            "for you in the next 90 days? Be specific. Number of clients, "
            "price point, revenue target, or specific milestone."
        ),
        base_weight=8,
        dependencies=("foundation.what_you_do",),
    ),
    BrandField(
        module="foundation",
        key="current_clients",
        label="Current Clients",
        question=(
            "Who is paying you right now? If no one, who do you want paying "
            "you and why?"
        ),
        base_weight=9,
        dependencies=("foundation.what_you_do",),
    ),
    BrandField(
        module="foundation",
        key="previous_attempts",
        label="Previous Attempts",
        question=(
            "What have you tried before? Courses, coaches, content, ads. "
            "What worked? What failed? Why did you stop?"
        ),
        base_weight=6,
        dependencies=("foundation.what_you_do",),
    ),
    # Logistics fields
    BrandField(
        module="foundation",
        key="time_available",
        label="Time Available",
        question=(
            "How much time per week can you realistically dedicate to "
            "content creation? Be honest."
        ),
        base_weight=4,
        dependencies=("foundation.what_you_do",),
        is_required=False,
    ),
    BrandField(
        module="foundation",
        key="camera_comfort",
        label="Camera Comfort",
        question=(
            "Are you comfortable on camera? Yes, no, or 'will do it but "
            "hate it'?"
        ),
        base_weight=3,
        dependencies=("foundation.what_you_do",),
        is_required=False,
    ),
    BrandField(
        module="foundation",
        key="platforms",
        label="Platforms",
        question=(
            "Which 1-2 platforms do you want to focus on? YouTube, LinkedIn, "
            "Twitter/X, TikTok, Instagram?"
        ),
        base_weight=5,
        dependencies=("foundation.what_you_do",),
        is_required=False,
    ),
    BrandField(
        module="foundation",
        key="existing_assets",
        label="Existing Assets",
        question=(
            "Do you have any existing content, presentations, workshops, or "
            "materials that can be repurposed?"
        ),
        base_weight=3,
        dependencies=("foundation.what_you_do",),
        is_required=False,
    ),
    BrandField(
        module="foundation",
        key="budget",
        label="Budget",
        question=(
            "What is your budget for tools, ads, and distribution? Even if "
            "it is zero, tell me."
        ),
        base_weight=2,
        dependencies=("foundation.what_you_do",),
        is_required=False,
    ),
]


# ── Module 2: Authority ───────────────────────────────────────

AUTHORITY_FIELDS = [
    BrandField(
        module="authority",
        key="unfair_advantage",
        label="Unfair Advantage",
        question=(
            "What is your unfair advantage? The experience, credentials, "
            "results, or stories that make you THE person who should be "
            "talking about this topic."
        ),
        base_weight=8,
        dependencies=("foundation.what_you_do",),
    ),
    BrandField(
        module="authority",
        key="results_achieved",
        label="Results Achieved",
        question=(
            "What specific results have you gotten for yourself or others? "
            "Numbers preferred. 'Helped client go from X to Y in Z months.'"
        ),
        base_weight=7,
        dependencies=("foundation.what_you_do",),
    ),
    BrandField(
        module="authority",
        key="contrarian_viewpoint",
        label="Contrarian Viewpoint",
        question=(
            "What do you believe that most people in your industry disagree "
            "with? The opinion that makes you interesting and memorable."
        ),
        base_weight=7,
        dependencies=("foundation.what_you_do", "authority.unfair_advantage"),
    ),
    BrandField(
        module="authority",
        key="common_mistakes",
        label="Common Mistakes",
        question=(
            "What mistakes do you see people in your space making repeatedly? "
            "Each mistake becomes a content topic."
        ),
        base_weight=6,
        dependencies=("foundation.what_you_do",),
    ),
    BrandField(
        module="authority",
        key="who_they_admire",
        label="Who They Admire",
        question=(
            "Who do you admire in your space and why? Used for competitive "
            "positioning, not copying."
        ),
        base_weight=5,
        dependencies=("foundation.what_you_do",),
    ),
]


# ── Module 3: Ideal Client Avatar (ICA) ──────────────────────

ICA_FIELDS = [
    BrandField(
        module="ica",
        key="one_sentence_identity",
        label="One-Sentence Identity",
        question=(
            "Describe your ideal client in one sentence. Psychographics, not "
            "demographics. What they are struggling with, what keeps them up "
            "at night."
        ),
        base_weight=8,
        dependencies=("foundation.what_you_do", "foundation.current_clients"),
    ),
    BrandField(
        module="ica",
        key="current_situation",
        label="Current Situation",
        question=(
            "What does your ideal client's life or business look like right "
            "now before working with you?"
        ),
        base_weight=7,
        dependencies=("ica.one_sentence_identity",),
    ),
    BrandField(
        module="ica",
        key="client_goals",
        label="Client Goals",
        question="What does your ideal client want to achieve?",
        base_weight=7,
        dependencies=("ica.one_sentence_identity",),
    ),
    BrandField(
        module="ica",
        key="pain_points",
        label="Pain Points",
        question="What frustrates your ideal client the most?",
        base_weight=7,
        dependencies=("ica.one_sentence_identity",),
    ),
    BrandField(
        module="ica",
        key="language_they_use",
        label="Language They Use",
        question=(
            "What actual words and phrases does your ideal client use to "
            "describe their problem? Not professional jargon. The words they "
            "type into Google at 2am."
        ),
        base_weight=7,
        dependencies=("ica.pain_points",),
    ),
    BrandField(
        module="ica",
        key="words_they_hate",
        label="Words They Hate",
        question=(
            "What words and phrases make your ideal client tune out or lose "
            "trust?"
        ),
        base_weight=5,
        dependencies=("ica.one_sentence_identity",),
    ),
    BrandField(
        module="ica",
        key="action_triggers",
        label="Action Triggers",
        question=(
            "What triggers your ideal client to finally take action and seek "
            "help?"
        ),
        base_weight=6,
        dependencies=("ica.pain_points",),
    ),
    BrandField(
        module="ica",
        key="what_theyve_tried",
        label="What They Have Tried",
        question=(
            "What solutions has your ideal client already tried? Other "
            "coaches, courses, DIY, free content?"
        ),
        base_weight=5,
        dependencies=("ica.one_sentence_identity",),
    ),
    BrandField(
        module="ica",
        key="objections_before_buying",
        label="Objections Before Buying",
        question=(
            "What are the reasons your ideal client hesitates before "
            "purchasing?"
        ),
        base_weight=6,
        dependencies=("ica.one_sentence_identity",),
    ),
    BrandField(
        module="ica",
        key="5_second_hook",
        label="5-Second Hook",
        question=(
            "What would make your ideal client say 'this is exactly what I "
            "need' within 5 seconds of seeing your content? This becomes your "
            "hook filter."
        ),
        base_weight=7,
        dependencies=(
            "ica.one_sentence_identity",
            "ica.pain_points",
            "ica.client_goals",
        ),
    ),
]


# ── Module 4: Positioning ─────────────────────────────────────

POSITIONING_FIELDS = [
    BrandField(
        module="positioning",
        key="positioning_statement",
        label="Positioning Statement",
        question=(
            "Let us build your positioning statement. The formula: 'I help "
            "[specific person] who is struggling with [specific problem] "
            "achieve [specific outcome] through [your unique method], without "
            "[the thing they fear about alternatives].' It must be specific "
            "enough that a 12-year-old could understand it."
        ),
        base_weight=9,
        dependencies=(
            "authority.unfair_advantage",
            "ica.one_sentence_identity",
            "ica.pain_points",
            "ica.client_goals",
        ),
    ),
    BrandField(
        module="positioning",
        key="key_differentiators",
        label="Key Differentiators",
        question=(
            "What makes you impossible to confuse with anyone else in your "
            "space? The specific gap you fill."
        ),
        base_weight=7,
        dependencies=("positioning.positioning_statement",),
    ),
]


# ── Module 5: Voice and Tone ──────────────────────────────────

VOICE_FIELDS = [
    BrandField(
        module="voice",
        key="voice_identity",
        label="Voice Identity",
        question=(
            "In one sentence, how do you communicate? What is YOUR voice?"
        ),
        base_weight=6,
        dependencies=("foundation.what_you_do",),
    ),
    BrandField(
        module="voice",
        key="personality_traits",
        label="Personality Traits",
        question=(
            "What are your top 5 personality traits, ranked in order of "
            "dominance?"
        ),
        base_weight=6,
        dependencies=("voice.voice_identity",),
    ),
    BrandField(
        module="voice",
        key="communication_style",
        label="Communication Style",
        question=(
            "Short or long form? Formal or casual? Story-driven or "
            "data-driven? High energy or calm authority?"
        ),
        base_weight=6,
        dependencies=("voice.voice_identity",),
    ),
    BrandField(
        module="voice",
        key="phrases_to_use",
        label="Phrases to Use",
        question=(
            "What words, phrases, and expressions do you naturally use? Your "
            "linguistic fingerprint."
        ),
        base_weight=6,
        dependencies=("voice.voice_identity",),
    ),
    BrandField(
        module="voice",
        key="phrases_to_avoid",
        label="Phrases to Avoid",
        question=(
            "What words, phrases, and expressions do NOT sound like you and "
            "should never appear in your content?"
        ),
        base_weight=5,
        dependencies=("voice.voice_identity",),
    ),
    BrandField(
        module="voice",
        key="formatting_preferences",
        label="Formatting Preferences",
        question=(
            "How do you prefer content to be structured? Short paragraphs, "
            "emoji usage, all caps for emphasis, etc."
        ),
        base_weight=4,
        dependencies=("voice.voice_identity",),
        is_required=False,
    ),
]


# ── Module 6: Offer ───────────────────────────────────────────

OFFER_FIELDS = [
    BrandField(
        module="offer",
        key="dream_outcome",
        label="Dream Outcome",
        question=(
            "What is the dream outcome you deliver for clients? The big "
            "transformation."
        ),
        base_weight=7,
        dependencies=("foundation.90_day_goal", "positioning.positioning_statement"),
    ),
    BrandField(
        module="offer",
        key="proof_of_delivery",
        label="Proof of Delivery",
        question=(
            "What evidence do you have that you can actually deliver this "
            "result? This increases perceived likelihood."
        ),
        base_weight=6,
        dependencies=("offer.dream_outcome",),
    ),
    BrandField(
        module="offer",
        key="time_to_result",
        label="Time to Result",
        question=(
            "How fast do you deliver the result? This decreases time delay "
            "in the value equation."
        ),
        base_weight=6,
        dependencies=("offer.dream_outcome",),
    ),
    BrandField(
        module="offer",
        key="ease_for_client",
        label="Ease for Client",
        question=(
            "How easy is it for the client? What effort do they need to put "
            "in? This decreases effort and sacrifice."
        ),
        base_weight=5,
        dependencies=("offer.dream_outcome",),
    ),
    BrandField(
        module="offer",
        key="deliverables",
        label="Deliverables",
        question=(
            "What specific things does the client get? List each component "
            "of your value stack separately."
        ),
        base_weight=6,
        dependencies=("offer.dream_outcome",),
    ),
    BrandField(
        module="offer",
        key="price",
        label="Price",
        question=(
            "What is the actual price? Position it as a steal compared to "
            "your value stack."
        ),
        base_weight=5,
        dependencies=("offer.deliverables",),
    ),
    BrandField(
        module="offer",
        key="guarantee",
        label="Guarantee",
        question=(
            "What guarantee or risk reversal eliminates buyer hesitation?"
        ),
        base_weight=5,
        dependencies=("offer.dream_outcome",),
    ),
]


# ── Module 7: Content Pillars ─────────────────────────────────

CONTENT_PILLARS_FIELDS = [
    BrandField(
        module="content_pillars",
        key="pillar_1_pain_awareness",
        label="Pain Awareness Pillar",
        question=(
            "Let us build your Pain and Problem Awareness pillar. This is "
            "content that makes your audience feel seen. Give me the recurring "
            "pains, frustrations, and problems your audience faces."
        ),
        base_weight=6,
        dependencies=(
            "foundation.what_you_do",
            "authority.unfair_advantage",
            "ica.pain_points",
        ),
    ),
    BrandField(
        module="content_pillars",
        key="pillar_2_method_framework",
        label="Method & Framework Pillar",
        question=(
            "Now your Method and Framework pillar. This shows your unique "
            "approach, system, and intellectual property. What is your "
            "methodology? What frameworks do you use?"
        ),
        base_weight=6,
        dependencies=(
            "foundation.what_you_do",
            "authority.unfair_advantage",
        ),
    ),
    BrandField(
        module="content_pillars",
        key="pillar_3_proof_results",
        label="Proof & Results Pillar",
        question=(
            "Your Proof and Results pillar. Content that demonstrates results "
            "through stories, case studies, and before/afters. What stories "
            "and results can we showcase?"
        ),
        base_weight=6,
        dependencies=("authority.results_achieved",),
    ),
    BrandField(
        module="content_pillars",
        key="pillar_4_belief_shifting",
        label="Belief Shifting Pillar",
        question=(
            "Optional but powerful: your Belief Shifting pillar. Contrarian "
            "content that challenges audience assumptions. What beliefs does "
            "your audience hold that are wrong or incomplete?"
        ),
        base_weight=5,
        dependencies=("authority.contrarian_viewpoint",),
        is_required=False,
    ),
]


# ── Module 8: Competitive Positioning ─────────────────────────

COMPETITIVE_FIELDS = [
    BrandField(
        module="competitive",
        key="competitors",
        label="Competitors",
        question=(
            "Name 3-5 competitors or alternatives in your space. Include "
            "'doing nothing' and 'DIY' as alternatives."
        ),
        base_weight=5,
        dependencies=("positioning.positioning_statement",),
    ),
    BrandField(
        module="competitive",
        key="competitor_strengths",
        label="Competitor Strengths",
        question="What does each competitor do well? Be honest.",
        base_weight=5,
        dependencies=("competitive.competitors",),
    ),
    BrandField(
        module="competitive",
        key="competitor_weaknesses",
        label="Competitor Weaknesses",
        question=(
            "Where does each competitor fall short? Not trash talk. Real gaps "
            "their audience complains about."
        ),
        base_weight=5,
        dependencies=("competitive.competitors",),
    ),
    BrandField(
        module="competitive",
        key="user_differentiator",
        label="Your Differentiator",
        question=(
            "How are you specifically different from each competitor?"
        ),
        base_weight=6,
        dependencies=("competitive.competitor_weaknesses",),
    ),
    BrandField(
        module="competitive",
        key="market_gap",
        label="Market Gap",
        question=(
            "What is the gap in the market that you uniquely fill?"
        ),
        base_weight=6,
        dependencies=(
            "competitive.competitor_weaknesses",
            "positioning.key_differentiators",
        ),
    ),
]


# ── Registry: All fields indexed by full key ──────────────────

ALL_FIELDS: List[BrandField] = (
    FOUNDATION_FIELDS
    + AUTHORITY_FIELDS
    + ICA_FIELDS
    + POSITIONING_FIELDS
    + VOICE_FIELDS
    + OFFER_FIELDS
    + CONTENT_PILLARS_FIELDS
    + COMPETITIVE_FIELDS
)

FIELDS_BY_KEY: Dict[str, BrandField] = {
    f"{f.module}.{f.key}": f for f in ALL_FIELDS
}

MODULES = [
    "foundation",
    "authority",
    "ica",
    "positioning",
    "voice",
    "offer",
    "content_pillars",
    "competitive",
]

MODULE_LABELS = {
    "foundation": "Foundation",
    "authority": "Authority",
    "ica": "Ideal Client Avatar",
    "positioning": "Positioning",
    "voice": "Voice & Tone",
    "offer": "Offer",
    "content_pillars": "Content Pillars",
    "competitive": "Competitive Positioning",
}

FIELDS_BY_MODULE: Dict[str, List[BrandField]] = {}
for _f in ALL_FIELDS:
    FIELDS_BY_MODULE.setdefault(_f.module, []).append(_f)

TOTAL_REQUIRED_FIELDS = sum(1 for f in ALL_FIELDS if f.is_required)
TOTAL_FIELDS = len(ALL_FIELDS)


def get_field(full_key: str) -> Optional[BrandField]:
    """Look up a field by its full key (module.field_key)."""
    return FIELDS_BY_KEY.get(full_key)


def get_module_fields(module: str) -> List[BrandField]:
    """Get all fields for a module."""
    return FIELDS_BY_MODULE.get(module, [])


def get_required_fields() -> List[BrandField]:
    """Get all required fields across all modules."""
    return [f for f in ALL_FIELDS if f.is_required]
