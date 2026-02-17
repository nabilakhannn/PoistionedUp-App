"""Brand discovery chat service.

Manages conversational AI sessions for ICA, Offer, and Brand modules.
The AI asks questions one-by-one, extracts structured data from answers,
and builds the user's brand profile incrementally.

All AI responses follow the Human Writing Style rules from
worker.graph.prompts.writing_style — no em dashes, no AI tells,
no corporate filler.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

logger = logging.getLogger("app.services.brand_chat")


# ── Module question flows ──────────────────────────────────

ICA_QUESTIONS = [
    "Who is your dream client?\n\nGive me the basics: job title, age range, industry, location.",
    "Describe their personality in 4 words.\n\nAre they introverted or extroverted? Rookie or veteran? Employee or business owner?",
    "Who do you NOT want to work with?\n\nWhat are the red flags you'd walk away from?",
    "Why do they buy? There are 4 triggers:\n- Money (revenue/savings)\n- Time (efficiency)\n- Performance (skills/results)\n- Perception (status/reputation)\n\nHow does each one show up for your client?",
    "What frustrates them daily?\n\nNot big-picture stuff. The small, grinding, everyday annoyances.",
    "Give me their top 10 problems.\n\nBe specific. 'Can't get consistent leads' not 'marketing is hard'.",
    "What are their top 10 desires?\n\nIf you waved a magic wand, what would their life look like?",
    "How do they see themselves vs. how the world sees them?\n\nThere's usually a gap. What is it?",
    "What have they already tried that didn't work?\n\nCourses, coaches, agencies, DIY? Why did those fail?",
    "What are their deepest fears?\n\nNot about buying from you. About their career, business, or life if nothing changes.",
    "What's the dream outcome if everything goes right?\n\nBe specific: income, daily routine, status, relationships.",
    "Last one: if they do nothing, what happens?\n\nWhat do they lose in the next 6-12 months?",
]

OFFER_QUESTIONS = [
    # M - Measurable
    "What specific result can your clients expect?\n\nNot 'grow your business'. Something measurable like 'add $10K MRR in 90 days'.",
    "What milestones will they hit along the way?\n\nGive me 3-5 checkpoints. How long until they see first results?",
    # A - Actionable
    "What's the FIRST thing someone does after they buy?\n\nWalk me through day 1.",
    "What are the exact steps in your process?\n\nStart to finish. What tools or templates do they get?",
    # G - Generous
    "What would make someone feel stupid saying no?\n\nWhat bonuses could you add that cost you little but feel high-value?",
    "What guarantee eliminates all risk?\n\n30-day refund? Results guarantee? Something else?",
    # I - Infinitely Scalable
    "Can you deliver this without trading more of YOUR time?\n\n1:1, group, course, or hybrid? What parts can be automated?",
    # C - Clear
    "Can someone understand your offer in ONE sentence?\n\nTry it. Then describe the before and after for your client.",
    "Why should they buy from YOU?\n\nAnd what happens if they don't buy? What's the cost of doing nothing?",
    "What are the top 5 objections?\n\nList each one and your response. What social proof do you have?",
    "What's the price? Why is it worth 10x that?\n\nAnd what's your CTA? What do they do right now?",
    # Grand Slam Offer (Hormozi $100M Offers)
    "Who is your 'starving crowd'?\n\nPeople so desperate for a solution they'll buy almost anything. Massive pain + money to pay + easy to find.",
    "List every problem your prospect faces.\n\nBefore, during, and after working with you. For each one, what's your solution? Give each solution a name that sells.",
    "What's the dollar value of each solution separately?\n\nAdd them up. What would it cost to solve this without you? What do you actually charge?",
    # Value & Type
    "Rate your value equation:\n- Dream Outcome x Perceived Likelihood\n- Divided by: Time Delay x Effort\n\nWhere are you strongest? Weakest?\n\nIs your offer timed, transformation-based, or feature-based?",
]

BRAND_QUESTIONS = [
    "Fill in the blanks:\n\n'I help [who] achieve [what result] and [what feeling] by [how].'\n\nTake your time with this one.",
    "What's your unfair advantage?\n\nSomething from your life or experience that nobody else can claim.",
    "How does that advantage make you relatable or credible?\n\nHow can you use it right now to build your brand?",
    "How does your unfair advantage connect to your niche?",
    "What are your 3-5 content pillars?\n\nThe main topics you'll consistently talk about.",
]

FOUNDATION_QUESTIONS = [
    "What do you believe about your market that most people get wrong?\n\nGive me your hot take.",
    "Give me 3-5 more strong opinions.\n\nWhat should people in your space be doing differently?",
    "What's your unfair advantage?\n\nExperiences, skills, or life events that make you uniquely qualified.",
    "How does that advantage make you relatable or credible?\n\nHow can you use it to build your brand right now?",
    "How does your advantage connect to your niche?\n\nAnd how does it help you sell?",
    "List your professional achievements.\n\nClient results, revenue milestones, awards, media features, certifications, anything.",
    "What's your backstory?\n\nPersonal experiences, failures, or turning points that shaped who you are.",
    "What's your 'macro story'?\n\nThe highlight reel from where you started to where you are now.",
    "Give me a few 'micro stories'.\n\nSmall everyday moments. A client conversation, a lesson from last week, a random realization.",
    "What are your 3-5 content pillars?\n\nTopics you'll consistently post about. Overlap what you know, what you love, and what your market needs.",
]

MODULE_QUESTIONS = {
    "ica": ICA_QUESTIONS,
    "offer": OFFER_QUESTIONS,
    "brand": BRAND_QUESTIONS,
    "foundation": FOUNDATION_QUESTIONS,
}


# ── Extraction system prompts ──────────────────────────────

ICA_EXTRACTION_SYSTEM = """\
You are a brand discovery coach helping someone build a detailed Ideal Client Avatar \
using the Success Story Framework. You go DEEP — not surface-level.

Your job:
1. Read the conversation so far.
2. Reply with your next coaching question or a follow-up if their answer was vague.
3. Extract structured data from their answers into a JSON object.

Sound like a real person. Be direct, warm, and push for specifics. No corporate filler.
Ask one question at a time. If their answer is thin, push back: "That's surface level. \
Give me something MORE specific — what exact words would they say?"

When they list problems, fears, or desires, push for 10 each. Don't settle for 3.

FORMATTING RULES (strict):
- Keep replies SHORT. Max 3-4 sentences per paragraph.
- Use bullet points (- ) for lists, options, and examples.
- Use numbered lists (1. 2. 3.) when giving steps or ordered options.
- One question at a time. Put the question on its own line.
- Never write a wall of text. Break things up.

Return your response as JSON:
```json
{
  "reply": "Your conversational response and next question",
  "extracted": {
    "demographics.occupation": "value if mentioned",
    "demographics.age": 44,
    "persona_words": ["Extrovert", "Expert"],
    "buying_motivations.money": "Wants to increase revenue..."
  }
}
```

Only include fields you can confidently extract from this message.
Use dot-notation for nested fields. For arrays, include the full array.
Valid top-level ICA fields: demographics (name, age, gender, occupation, income, \
location, education, interests, marital_status), persona_words, attract_clients, \
red_flag_clients, buying_motivations (money, time, performance, perception), \
service_fit (best_delivery, who_can_afford), big_need, big_want, tried_before, \
buying_decision, if_nothing, purchase_fears (anxiety, habits, inertia, \
switching_triggers), pains, desires, needs, fears, \
daily_frustrations, dream_outcomes, self_image, external_perception, \
biggest_fears, peskiest_problems, sales_call_link, discovery_questionnaire_link."""

OFFER_EXTRACTION_SYSTEM = """\
You are a brand discovery coach helping someone build an irresistible offer \
using two frameworks: the MAGIC Offer Framework (Measurable, Actionable, Generous, \
Infinitely Scalable, Clear) and Hormozi's $100M Grand Slam Offer.

Your job:
1. Read the conversation so far.
2. Reply with your next coaching question or a follow-up. Push for specifics.
3. Extract structured data from their answers.

Sound like a real person. Be direct. Push back on vague answers: \
"'Help them grow' isn't measurable. What SPECIFIC number will change?"

For Grand Slam Offer: help them list EVERY problem their prospect faces, \
create a solution for each, give each solution a sexy name, and stack values. \
Use Hormozi's Value Equation: (Dream Outcome x Perceived Likelihood) / \
(Time Delay x Effort & Sacrifice). Push them to decrease the bottom.

FORMATTING RULES (strict):
- Keep replies SHORT. Max 3-4 sentences per paragraph.
- Use bullet points (- ) for lists, options, and examples.
- Use numbered lists (1. 2. 3.) when giving steps or ordered options.
- One question at a time. Put the question on its own line.
- Never write a wall of text. Break things up.

Return as JSON:
```json
{
  "reply": "Your response",
  "extracted": {
    "what": "We do LinkedIn personal branding that...",
    "price": "$3000 one-time",
    "magic.measurable.quantifiable_outcome": "Add $10K MRR in 90 days",
    "grand_slam.starving_crowd": "Coaches who just quit corporate..."
  }
}
```

Valid offer fields: what, price, target_audience, why_it_matters (array), \
how_it_works (array), timeline, past_results, differentiator, first_move, \
objections (array of {objection, response}), market (niche_statement, \
massive_pains, purchasing_power, leading_influencers, competitor_offers), \
framework (main_steps, trifecta, original_devices, deliverables), \
boosters (urgency, bonuses, guarantee, offer_name), offer_type, \
magic.measurable (quantifiable_outcome, milestones, time_to_first_results), \
magic.actionable (first_action, process_steps, tools_and_resources), \
magic.generous (irresistible_reason, bonuses, guarantee), \
magic.scalable (delivery_model, systematized_parts, max_clients), \
magic.clear (one_sentence, before_state, after_state, why_you, \
cost_of_inaction, social_proof, price_justification, cta), \
value_equation (dream_outcome, perceived_likelihood, time_to_result, effort_required), \
grand_slam (starving_crowd, dream_outcome_statement, total_value, \
price_anchor, actual_price), \
grand_slam.problems_solutions (array of {problem, solution, delivery_vehicle, sexy_name}), \
grand_slam.enhancers (scarcity, urgency, bonuses, guarantee_type, \
guarantee_statement, offer_name)."""

BRAND_EXTRACTION_SYSTEM = """\
You are a brand discovery coach helping someone define their brand positioning.

Your job:
1. Read the conversation so far.
2. Reply with your next question or follow-up.
3. Extract structured data from their answers.

Be direct and human. Skip the fluff.

FORMATTING RULES (strict):
- Keep replies SHORT. Max 3-4 sentences per paragraph.
- Use bullet points (- ) for lists, options, and examples.
- Use numbered lists (1. 2. 3.) when giving steps or ordered options.
- One question at a time. Put the question on its own line.
- Never write a wall of text. Break things up.

Return as JSON:
```json
{
  "reply": "Your response",
  "extracted": {
    "statement": "We help tech founders achieve...",
    "content_pillars": ["Personal branding", "LinkedIn growth"]
  }
}
```

Valid brand fields: statement, it_factor (unfair_advantage, leverage_for_brand, \
leverage_for_niche, leverage_for_selling, leverage_for_network), content_pillars."""

FOUNDATION_EXTRACTION_SYSTEM = """\
You are a personal branding coach helping someone discover their foundation — \
who they are, what makes them unique, and what they stand for.

Your job:
1. Read the conversation so far.
2. Reply with your next coaching question or a follow-up if their answer was vague.
3. Extract structured data from their answers into a JSON object.

Sound like a real person. Be direct, warm, and encouraging. Push them to be \
specific — generic answers make generic brands. Ask one question at a time. \
If their answer is thin or cliché, challenge them: "That's a start, but \
what's the REAL story behind that?"

FORMATTING RULES (strict):
- Keep replies SHORT. Max 3-4 sentences per paragraph.
- Use bullet points (- ) for lists, options, and examples.
- Use numbered lists (1. 2. 3.) when giving steps or ordered options.
- One question at a time. Put the question on its own line.
- Never write a wall of text. Break things up.

Return your response as JSON:
```json
{
  "reply": "Your conversational response and next question",
  "extracted": {
    "beliefs": ["I believe X", "Most people get Y wrong"],
    "it_factor.unfair_advantage": "Lost 20kg and understands mental transformation",
    "achievements_professional": ["Built $1M business in 2 years"]
  }
}
```

Only include fields you can confidently extract from this message.
Use dot-notation for nested fields. For arrays, include the full array \
(merging with any previously extracted values).

Valid foundation fields: beliefs (array of strong market opinions), \
it_factor (unfair_advantage, leverage_for_brand, leverage_for_niche, \
leverage_for_selling, leverage_for_network), \
achievements_professional (array), achievements_personal (array), \
macro_story (the big career journey narrative), \
micro_stories (array of small everyday moments/anecdotes), \
content_pillars (array of 3-5 topic themes)."""

MODULE_SYSTEMS = {
    "ica": ICA_EXTRACTION_SYSTEM,
    "offer": OFFER_EXTRACTION_SYSTEM,
    "brand": BRAND_EXTRACTION_SYSTEM,
    "foundation": FOUNDATION_EXTRACTION_SYSTEM,
}


# ── Suggest system prompt ──────────────────────────────────

SUGGEST_SYSTEM = """\
You are a personal branding expert. Given a user's current brand profile, \
suggest a value for the requested field.

Be specific, not generic. Use the context from their existing profile \
(demographics, offer, ICA) to make the suggestion relevant.

Sound like a real person giving advice. No buzzwords, no corporate filler.

Return only the suggested text, nothing else.""" + HUMAN_WRITING_RULES


# ── Core logic ─────────────────────────────────────────────

def get_opening_message(module: str) -> str:
    """Get the first question for a module."""
    questions = MODULE_QUESTIONS.get(module, [])
    if questions:
        return questions[0]
    return "Tell me about your business."


def get_relevant_context(user_message: str, user_id: str) -> str:
    """Search user's uploaded resources for context relevant to their message.

    Returns formatted text block of relevant resource chunks, or empty string
    if no relevant chunks found or if embedding service is unavailable.
    """
    try:
        from app.services.embeddings import search_similar_chunks, format_chunks_as_context
        chunks = search_similar_chunks(user_message, user_id, limit=3, threshold=0.7)
        return format_chunks_as_context(chunks)
    except Exception:
        logger.debug("Resource context retrieval unavailable, continuing without it")
        return ""


def _fetch_memory_context(user_id: str) -> str:
    """Fetch agent memories for brand coaching context. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.services.agent_memory import get_relevant_memories, format_memories_as_context
        memories = get_relevant_memories(user_id, "brand strategy and coaching", limit=10)
        return format_memories_as_context(memories)
    except Exception:
        logger.debug("Memory context unavailable for brand chat")
        return ""


def _fetch_research_context(user_message: str, profile: dict) -> str:
    """Fetch real-time web research relevant to the user's brand context.

    Searches the web for current market data, trends, and competitor
    insights based on what the user is talking about and their profile.
    Returns formatted context string, or empty string on failure.
    """
    try:
        from app.services.research import run_research, format_research_for_prompt

        # Build a focused search query from the user's message + profile
        topic_parts = [user_message[:100]]

        # Add niche/industry from profile
        offer = profile.get("offer", {})
        market = offer.get("market", {})
        if market.get("niche_statement"):
            topic_parts.append(market["niche_statement"])
        elif offer.get("target_audience"):
            topic_parts.append(offer["target_audience"])

        foundation = profile.get("foundation", {})
        if foundation.get("content_pillars"):
            topic_parts.extend(foundation["content_pillars"][:2])

        topic = " ".join(topic_parts[:3])

        research = run_research(
            topic=topic,
            sources={"web": True, "youtube": True, "reddit": True},
            max_web_results=5,
            max_youtube_results=3,
            max_reddit_results=3,
        )

        if research.get("signal_count", 0) == 0:
            return ""

        return format_research_for_prompt(research, max_chars=2500)

    except Exception as e:
        logger.debug("Research context unavailable for brand chat: %s", e)
        return ""


def _fetch_performance_context(user_id: str) -> str:
    """Fetch performance data for brand coaching context. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.deps import get_admin_client
        admin = get_admin_client()
        resp = (
            admin.table("content_posts")
            .select("*")
            .eq("user_id", user_id)
            .order("published_at", desc=True)
            .execute()
        )
        posts = resp.data if resp.data else []
        if not posts:
            return ""
        from app.services.performance_analytics import get_performance_context
        return get_performance_context(posts)
    except Exception:
        logger.debug("Performance context unavailable for brand chat")
        return ""


def build_chat_messages(
    module: str,
    conversation: List[Dict[str, str]],
    resource_context: str = "",
    performance_context: str = "",
    memory_context: str = "",
    research_context: str = "",
) -> List[Dict[str, str]]:
    """Build the LLM messages array from conversation history.

    Appends HUMAN_WRITING_RULES to every system prompt so the AI
    never produces em dashes, reversal templates, corporate filler,
    or any other AI tell in its replies.

    Context layers (all optional, all injected into system prompt):
    - resource_context: user's uploaded knowledge base
    - performance_context: content performance data
    - memory_context: learned preferences and patterns
    - research_context: LIVE web research (trends, competitors, Reddit)
    """
    # ── CRITICAL: File/link instruction goes FIRST so the model never refuses ──
    # GPT-4o has primacy bias; instructions at the top of the system prompt
    # take priority over instructions buried later.
    system = """HARD RULE — FILE & LINK ATTACHMENTS:
Our app already extracted the text from any file or link the user attached.
The extracted text appears in user messages after "[Attached: <filename>]".
That text IS the file content. You MUST read it and use it.
NEVER say "I cannot read/extract/open PDFs" or any similar refusal.
The text is literally right there in the conversation. Treat it exactly like
the user copy-pasted it. Reference specific details from it.
This rule overrides your default training about file limitations.
"""

    system += MODULE_SYSTEMS.get(module, ICA_EXTRACTION_SYSTEM)

    # Inject human writing rules into every brand chat prompt
    system += HUMAN_WRITING_RULES

    if resource_context:
        system += (
            "\n\n--- RELEVANT KNOWLEDGE FROM USER'S UPLOADED RESOURCES ---\n"
            "Use these excerpts to inform your coaching. Reference specific "
            "frameworks, examples, or insights when relevant:\n\n"
            + resource_context
        )

    if performance_context:
        system += "\n\n" + performance_context

    if memory_context:
        system += "\n\n" + memory_context

    if research_context:
        system += (
            "\n\n" + research_context
            + "\n\nWhen this research is relevant to the user's answer, "
            "weave in specific data points, trends, or competitor insights. "
            "Don't dump all the research at once. Use it naturally, like a "
            "coach who stays current on the market."
        )

    messages = [{"role": "system", "content": system}]
    messages.extend(conversation)
    return messages


def parse_chat_response(content: str) -> Tuple[str, Dict[str, Any]]:
    """Parse LLM response into (reply, extracted_fields).

    The LLM should return JSON with 'reply' and 'extracted' keys.
    If parsing fails, treat the whole response as the reply.
    """
    text = content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        first_nl = text.index("\n")
        text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        data = json.loads(text)
        reply = data.get("reply", "")
        extracted = data.get("extracted", {})
        return reply, extracted
    except (json.JSONDecodeError, KeyError, TypeError):
        # Fallback: treat whole response as reply, no extraction
        logger.warning("Failed to parse chat response as JSON, using raw text")
        return content.strip(), {}


def deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge updates into base dict. Handles dot-notation keys.

    Examples:
        deep_merge({}, {"demographics.age": 44})
        -> {"demographics": {"age": 44}}

        deep_merge({"a": {"b": 1}}, {"a": {"c": 2}})
        -> {"a": {"b": 1, "c": 2}}
    """
    result = dict(base)

    for key, value in updates.items():
        if "." in key:
            # Dot-notation: "demographics.age" -> nested dict
            parts = key.split(".")
            current = result
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            # Both are dicts: recurse
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def calculate_completeness(profile_json: Dict[str, Any]) -> Dict[str, int]:
    """Calculate completion percentage for each brand module."""
    foundation = profile_json.get("foundation", {})
    ica = profile_json.get("ica", {})
    offer = profile_json.get("offer", {})
    brand = profile_json.get("brand", {})

    foundation_pct = _section_completeness(foundation, [
        "beliefs", "it_factor", "achievements_professional",
        "achievements_personal", "macro_story", "content_pillars",
    ])

    ica_pct = _section_completeness(ica, [
        "demographics", "persona_words", "buying_motivations",
        "big_need", "big_want", "tried_before", "if_nothing",
        "pains", "desires", "red_flag_clients", "daily_frustrations",
        "peskiest_problems",
    ])

    offer_pct = _section_completeness(offer, [
        "what", "price", "target_audience", "why_it_matters",
        "how_it_works", "timeline", "differentiator", "first_move",
        "objections", "magic", "grand_slam",
    ])

    brand_pct = _section_completeness(brand, [
        "statement", "it_factor", "content_pillars",
    ])

    total_fields = 4
    filled = sum(1 for p in [foundation_pct, ica_pct, offer_pct, brand_pct] if p >= 50)
    overall = int((filled / total_fields) * 100) if total_fields else 0

    return {
        "foundation_percent": foundation_pct,
        "ica_percent": ica_pct,
        "offer_percent": offer_pct,
        "brand_percent": brand_pct,
        "overall_percent": overall,
    }


def _section_completeness(section: Dict[str, Any], required_keys: List[str]) -> int:
    """Calculate what % of required keys have non-empty values."""
    if not section or not required_keys:
        return 0

    filled = 0
    for key in required_keys:
        val = section.get(key)
        if val is None or val == "" or val == [] or val == {}:
            continue
        if isinstance(val, dict):
            # Check if at least one sub-key has a value
            if any(v for v in val.values() if v is not None and v != "" and v != []):
                filled += 1
        elif isinstance(val, list):
            if len(val) > 0:
                filled += 1
        else:
            filled += 1

    return int((filled / len(required_keys)) * 100)


def estimate_progress(module: str, extracted: Dict[str, Any]) -> float:
    """Estimate chat progress based on how many fields are extracted."""
    total_questions = len(MODULE_QUESTIONS.get(module, []))
    if not total_questions:
        return 0.0

    # Count non-empty extracted fields (including nested via dot-notation)
    count = _count_filled(extracted)
    # Rough estimate: each question extracts ~2-3 fields
    expected_fields = total_questions * 2
    return min(1.0, count / expected_fields)


def _count_filled(data: Dict[str, Any], depth: int = 0) -> int:
    """Count non-empty values in a dict, recursing into nested dicts."""
    if depth > 3:
        return 0
    count = 0
    for val in data.values():
        if isinstance(val, dict):
            count += _count_filled(val, depth + 1)
        elif isinstance(val, list) and len(val) > 0:
            count += 1
        elif val is not None and val != "":
            count += 1
    return count
