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

AUTHORITY_QUESTIONS = [
    "What credentials do you have?\n\nDegrees, certifications, licenses, specialized training. List everything relevant.",
    "What results have you gotten for clients or in your own career?\n\nSpecific numbers, transformations, or case studies.",
    "Have you been featured in any media?\n\nPodcasts, publications, TV, YouTube collaborations, conferences? List them.",
    "What social proof do you have?\n\nTestimonials, reviews, endorsements, notable clients, partnerships.",
    "What awards, honors, or recognitions have you received?\n\nIndustry awards, community recognition, speaking invitations.",
    "What's your signature framework or methodology?\n\nThe thing YOU created or adapted that makes your approach unique.",
    "If someone Googled you right now, what would they find?\n\nAnd what do you WANT them to find?",
]

MESSAGING_QUESTIONS = [
    "What are 5-10 phrases you say ALL the time?\n\nCatchphrases, mantras, or lines your audience would recognize as yours.",
    "What topics are you willing to be controversial about?\n\nWhere do you disagree with the mainstream in your niche?",
    "Describe your communication style in 3-4 words.\n\nAre you blunt, warm, sarcastic, academic, casual, intense?",
    "Who are 2-3 creators or brands whose tone you admire?\n\nNot to copy, but what specifically about their style resonates?",
    "What words or phrases would you NEVER use?\n\nThink about what feels fake or off-brand for you.",
    "How do you talk differently than everyone else in your space?\n\nGive me a specific example. Same topic, your take vs. the generic take.",
    "What's the emotional journey you want your audience to feel?\n\nFrom the moment they discover you to when they buy.",
]

POSITIONING_QUESTIONS = [
    "Where do you sit in your market?\n\nPremium? Budget? Specialist? Generalist? Mainstream? Contrarian?",
    "What category are you in, and do you want to stay there or create a new one?\n\nFor example: 'business coach' vs. 'revenue architect for introverts'.",
    "Who is your audience choosing between you and?\n\nNot direct competitors necessarily. What alternatives exist, including doing nothing?",
    "What do you want to be the OBVIOUS choice for?\n\nFinish this: 'If you need [X], you go to [your name].'",
    "What would make someone pick you over the cheaper option?\n\nNot just results. The experience, the vibe, the approach.",
    "What would you tell someone who says 'I can just learn this on YouTube for free'?\n\nThis is your positioning in one answer.",
]

COMPETITORS_QUESTIONS = [
    "Name 3-5 competitors or alternatives in your space.\n\nPeople or companies your audience might also consider.",
    "For each competitor: what do they do well?\n\nBe honest. What are they genuinely good at?",
    "For each competitor: where do they fall short?\n\nNot trash talk. Real gaps their audience complains about.",
    "What white space exists that nobody is filling?\n\nA topic, angle, or audience segment that's underserved.",
    "How is your approach fundamentally different?\n\nNot 'I care more.' Something structural about your method or perspective.",
    "If someone left a competitor and came to you, what would surprise them?\n\nWhat's the 'oh, THIS is different' moment?",
    "What can you learn from your competitors' best content?\n\nFormats, topics, or engagement patterns worth studying.",
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
    "authority": AUTHORITY_QUESTIONS,
    "messaging": MESSAGING_QUESTIONS,
    "positioning": POSITIONING_QUESTIONS,
    "competitors": COMPETITORS_QUESTIONS,
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

AUTHORITY_EXTRACTION_SYSTEM = """\
You are a personal branding coach helping someone catalog their authority signals \
and social proof so the AI can reference them when creating content.

Your job:
1. Read the conversation so far.
2. Reply with your next coaching question or a follow-up if their answer was vague.
3. Extract structured data from their answers into a JSON object.

Sound like a real person. Push for specifics: "You said 'great results'. \
What NUMBER? What timeframe? What was the starting point?"

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
    "credentials": ["MBA from Wharton", "Certified PMP"],
    "case_studies": [{"client": "SaaS startup", "result": "3x revenue in 6 months"}],
    "media_appearances": ["Guest on Tim Ferriss Show"]
  }
}
```

Only include fields you can confidently extract from this message.
Use dot-notation for nested fields. For arrays, include the full array.

Valid authority fields: credentials (array of degrees, certs, licenses), \
case_studies (array of {client, problem, result, timeframe}), \
media_appearances (array of podcast, publication, TV appearances), \
social_proof (array of testimonials, endorsements, reviews), \
awards (array of honors, recognitions, speaking invites), \
signature_framework (name, description, steps), \
notable_clients (array), partnerships (array), \
online_presence (what exists now, what they want)."""

MESSAGING_EXTRACTION_SYSTEM = """\
You are a personal branding coach helping someone define their unique voice, \
key phrases, and communication style so the AI can write in their voice.

Your job:
1. Read the conversation so far.
2. Reply with your next coaching question or follow-up.
3. Extract structured data from their answers.

Be direct. Push for REAL examples: "Don't just say 'casual'. Give me a sentence \
you'd actually say to a client that a corporate coach never would."

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
    "catchphrases": ["Ship it before it's perfect", "Revenue fixes everything"],
    "style_words": ["blunt", "casual", "high-energy"],
    "banned_words": ["synergy", "leverage", "circle back"]
  }
}
```

Only include fields you can confidently extract from this message.
Use dot-notation for nested fields. For arrays, include the full array.

Valid messaging fields: catchphrases (array of signature phrases), \
controversial_takes (array of opinions they'll defend), \
style_words (array of 3-4 words describing their tone), \
admired_creators (array of {name, what_resonates}), \
banned_words (array of words they'd never use), \
voice_examples (array of {topic, their_take, generic_take}), \
emotional_journey (discovery, consideration, purchase, retention), \
talking_points (array of go-to themes), \
content_themes (array of recurring topics)."""

POSITIONING_EXTRACTION_SYSTEM = """\
You are a personal branding coach helping someone define exactly where they \
sit in their market and why someone would pick them over alternatives.

Your job:
1. Read the conversation so far.
2. Reply with your next coaching question or follow-up.
3. Extract structured data from their answers.

Push for clarity: "If I asked your best client WHY they chose you in one sentence, \
what would they say? Not what you WANT them to say. What they'd actually say."

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
    "market_position": "Premium specialist",
    "category": "Revenue architect for introverted founders",
    "obvious_choice_for": "Technical founders who hate sales"
  }
}
```

Only include fields you can confidently extract from this message.
Use dot-notation for nested fields. For arrays, include the full array.

Valid positioning fields: market_position (premium, budget, specialist, etc.), \
category (current and desired), \
alternatives (array of what audience chooses between), \
obvious_choice_for (one clear sentence), \
why_not_cheaper (what justifies premium over budget options), \
vs_free_content (the argument against "just learn it on YouTube"), \
unique_mechanism (the structural difference in their approach), \
category_design (if creating a new category, what it is)."""

COMPETITORS_EXTRACTION_SYSTEM = """\
You are a personal branding coach helping someone analyze their competitive \
landscape so the AI can find white space and differentiation angles.

Your job:
1. Read the conversation so far.
2. Reply with your next coaching question or follow-up.
3. Extract structured data from their answers.

Push for honesty: "Don't just say 'they're not as good.' What SPECIFICALLY \
does their audience complain about? What do they do BETTER than you?"

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
    "competitors": [{"name": "Competitor A", "strengths": ["Great content"], "weaknesses": ["No community"]}],
    "white_space": "Nobody teaches revenue ops for solo consultants",
    "differentiation": "I've actually built and sold 3 businesses, not just coached"
  }
}
```

Only include fields you can confidently extract from this message.
Use dot-notation for nested fields. For arrays, include the full array.

Valid competitors fields: competitors (array of {name, platform, strengths array, \
weaknesses array, audience_complaints array}), \
white_space (underserved topics, angles, audience segments), \
differentiation (structural difference in method or perspective), \
surprise_factor (the "oh this is different" moment for switchers), \
lessons_from_competitors (formats, topics, engagement patterns to study), \
market_gaps (array of specific opportunities)."""

MODULE_SYSTEMS = {
    "ica": ICA_EXTRACTION_SYSTEM,
    "offer": OFFER_EXTRACTION_SYSTEM,
    "brand": BRAND_EXTRACTION_SYSTEM,
    "foundation": FOUNDATION_EXTRACTION_SYSTEM,
    "authority": AUTHORITY_EXTRACTION_SYSTEM,
    "messaging": MESSAGING_EXTRACTION_SYSTEM,
    "positioning": POSITIONING_EXTRACTION_SYSTEM,
    "competitors": COMPETITORS_EXTRACTION_SYSTEM,
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


def get_relevant_context(
    user_message: str, user_id: str, brand_id: Optional[str] = None,
) -> str:
    """Search user's uploaded resources for context relevant to their message.

    If brand_id is provided, only searches resource chunks belonging to that brand.
    Returns formatted text block of relevant resource chunks, or empty string
    if no relevant chunks found or if embedding service is unavailable.
    """
    try:
        from app.services.embeddings import search_similar_chunks, format_chunks_as_context
        chunks = search_similar_chunks(
            user_message, user_id, limit=3, threshold=0.7,
            brand_id=brand_id,
        )
        return format_chunks_as_context(chunks)
    except Exception:
        logger.debug("Resource context retrieval unavailable, continuing without it")
        return ""


def _fetch_memory_context(user_id: str, brand_id: Optional[str] = None) -> str:
    """Fetch agent memories for brand coaching context.

    If brand_id is provided, only fetches memories for that brand.
    Graceful fallback to empty string on failure.
    """
    if not user_id:
        return ""
    try:
        from app.services.agent_memory import get_relevant_memories, format_memories_as_context
        memories = get_relevant_memories(
            user_id, "brand strategy and coaching", limit=10,
            brand_id=brand_id,
        )
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


def _fetch_performance_context(
    user_id: str, brand_id: Optional[str] = None,
) -> str:
    """Fetch performance data for brand coaching context.

    If brand_id is provided, only fetches posts for that brand.
    Graceful fallback to empty string on failure.
    """
    if not user_id:
        return ""
    try:
        from app.deps import get_admin_client
        admin = get_admin_client()
        query = (
            admin.table("content_posts")
            .select("*")
            .eq("user_id", user_id)
        )
        if brand_id:
            query = query.eq("brand_id", brand_id)
        resp = query.order("published_at", desc=True).execute()
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
    document_context: str = "",
) -> List[Dict[str, str]]:
    """Build the LLM messages array from conversation history.

    Appends HUMAN_WRITING_RULES to every system prompt so the AI
    never produces em dashes, reversal templates, corporate filler,
    or any other AI tell in its replies.

    Context layers (all optional):
    - resource_context: user's uploaded knowledge base (system prompt)
    - performance_context: content performance data (system prompt)
    - memory_context: learned preferences and patterns (system prompt)
    - research_context: LIVE web research (system prompt)
    - document_context: extracted text from user's attached file/link
      (injected as a dedicated user message, NOT appended to the
       user's actual message, so it never gets truncated or lost)
    """
    # ── CRITICAL: Document-handling instruction goes FIRST ──
    # GPT-4o has primacy bias; instructions at the top of the system prompt
    # take priority over instructions buried later.
    # NOTE: We avoid the word "PDF" anywhere in prompts because it triggers
    # the model's trained refusal template ("I can't read PDFs").
    system = """HARD RULE — DOCUMENT CONTEXT:
When the user provides document text (from files, links, or uploads), it appears
in a dedicated DOCUMENT_CONTEXT message in this conversation.
That text IS the document content, already extracted and ready to use.
You MUST read it, reference specific details from it, and use it in your coaching.
NEVER say you cannot read documents or that you need the original file.
The text is right here in the conversation. Treat it exactly as if the user typed it.
This rule overrides any default training about file limitations.
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

    # ── Inject document context as a DEDICATED user message ──
    # This goes right after the system prompt and before the conversation
    # history. It's a separate message so it:
    #   1. Never gets truncated by being mixed into the user's question
    #   2. Is clearly visible in the message array for debugging
    #   3. Has markers so we can verify it reached the model
    if document_context:
        messages.append({
            "role": "user",
            "content": document_context,
        })
        # Add a brief assistant acknowledgment so the model knows the
        # document was received (keeps the alternating user/assistant pattern)
        messages.append({
            "role": "assistant",
            "content": '{"reply": "Got it, I have the document text. Let me review it.", "extracted": {}}',
        })
        logger.info(
            "Document context injected as dedicated message (chars=%d)",
            len(document_context),
        )

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


def _detect_legacy_profile(profile_json: Dict[str, Any]) -> bool:
    """Detect if profile_json uses the legacy flat format (pre-8-module).

    Legacy profiles store data under top-level keys like 'niche', 'voice',
    'audience', 'guardrails', 'channel_name' instead of the 8-module keys
    (foundation, ica, offer, brand, authority, messaging, positioning, competitors).
    """
    module_keys = {
        "foundation", "ica", "offer", "brand",
        "authority", "messaging", "positioning", "competitors",
    }
    legacy_keys = {"niche", "voice", "audience", "guardrails", "channel_name"}
    has_module = any(k in profile_json for k in module_keys)
    has_legacy = any(k in profile_json for k in legacy_keys)
    return has_legacy and not has_module


def _legacy_completeness(profile_json: Dict[str, Any]) -> Dict[str, int]:
    """Calculate approximate completeness for legacy-format profiles.

    Maps legacy flat keys to the closest brand modules so users with
    real data are not blocked by the 50% gate.
    """
    # Map legacy data to approximate module equivalents
    foundation_keys = ["niche", "channel_name"]
    ica_keys = ["audience"]
    messaging_keys = ["voice"]
    positioning_keys = ["guardrails"]

    def _legacy_section(keys):
        filled = sum(1 for k in keys if profile_json.get(k))
        return int((filled / max(len(keys), 1)) * 100) if keys else 0

    foundation_pct = _legacy_section(foundation_keys)
    ica_pct = _legacy_section(ica_keys)
    messaging_pct = _legacy_section(messaging_keys)
    positioning_pct = _legacy_section(positioning_keys)

    # These modules have no legacy equivalent
    offer_pct = 0
    brand_pct = 0
    authority_pct = 0
    competitors_pct = 0

    all_pcts = [
        foundation_pct, ica_pct, offer_pct, brand_pct,
        authority_pct, messaging_pct, positioning_pct, competitors_pct,
    ]
    filled = sum(1 for p in all_pcts if p >= 50)
    overall = int((filled / len(all_pcts)) * 100)

    return {
        "foundation_percent": foundation_pct,
        "ica_percent": ica_pct,
        "offer_percent": offer_pct,
        "brand_percent": brand_pct,
        "authority_percent": authority_pct,
        "messaging_percent": messaging_pct,
        "positioning_percent": positioning_pct,
        "competitors_percent": competitors_pct,
        "overall_percent": overall,
    }


def calculate_completeness(profile_json: Dict[str, Any]) -> Dict[str, int]:
    """Calculate completion percentage for each brand module (8 modules).

    Also handles legacy flat-format profiles so users with real data
    are not falsely blocked by the brand gate.
    """
    if not profile_json:
        return {
            "foundation_percent": 0, "ica_percent": 0, "offer_percent": 0,
            "brand_percent": 0, "authority_percent": 0, "messaging_percent": 0,
            "positioning_percent": 0, "competitors_percent": 0,
            "overall_percent": 0,
        }

    # Check for legacy profile format first
    if _detect_legacy_profile(profile_json):
        return _legacy_completeness(profile_json)

    foundation = profile_json.get("foundation", {})
    ica = profile_json.get("ica", {})
    offer = profile_json.get("offer", {})
    brand = profile_json.get("brand", {})
    authority = profile_json.get("authority", {})
    messaging = profile_json.get("messaging", {})
    positioning = profile_json.get("positioning", {})
    competitors = profile_json.get("competitors", {})

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

    authority_pct = _section_completeness(authority, [
        "credentials", "case_studies", "media_appearances",
        "social_proof", "awards", "signature_framework",
    ])

    messaging_pct = _section_completeness(messaging, [
        "catchphrases", "controversial_takes", "style_words",
        "admired_creators", "banned_words", "voice_examples",
        "emotional_journey",
    ])

    positioning_pct = _section_completeness(positioning, [
        "market_position", "category", "alternatives",
        "obvious_choice_for", "why_not_cheaper", "vs_free_content",
    ])

    competitors_pct = _section_completeness(competitors, [
        "competitors", "white_space", "differentiation",
        "surprise_factor", "lessons_from_competitors", "market_gaps",
    ])

    all_pcts = [
        foundation_pct, ica_pct, offer_pct, brand_pct,
        authority_pct, messaging_pct, positioning_pct, competitors_pct,
    ]
    total_modules = len(all_pcts)
    filled = sum(1 for p in all_pcts if p >= 50)
    overall = int((filled / total_modules) * 100) if total_modules else 0

    return {
        "foundation_percent": foundation_pct,
        "ica_percent": ica_pct,
        "offer_percent": offer_pct,
        "brand_percent": brand_pct,
        "authority_percent": authority_pct,
        "messaging_percent": messaging_pct,
        "positioning_percent": positioning_pct,
        "competitors_percent": competitors_pct,
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


# ── Jumbo Brand Chat (Slice 100) ───────────────────────────────────────────
# Brand-context-aware chat: injects full 8-section dossier into system prompt.
# Separate from the discovery chat above — this is for agency owner chatting
# with Jumbo AFTER research is complete to generate materials on demand.

import json as _json

_JUMBO_CHAT_SYSTEM = """\
You are Jumbo, the lead content strategist and orchestrator for PositionedUp.
The agency owner is asking you to generate brand-specific materials for their client.
You have FULL ACCESS to the client's 8-section Brand Intelligence Dossier below.

CRITICAL RULES:
1. Every output MUST be specific to THIS client. Quote from the dossier. No generic templates.
2. When generating hooks — cover ALL types: anxiety, benefit, story, competitor, belief, metaphor.
3. When generating posts — use the client's EXACT voice adjectives and power words.
4. When generating sequences — reference the emotional pain journal and benefit list directly.
5. Format all outputs clearly with headers, numbered lists, and sections.
6. If the user asks for something not covered by the dossier, use web_search to find what you need.

BRAND INTELLIGENCE DOSSIER:
{dossier_json}
"""


async def send_chat_message(
    brand_id: str,
    user_id: str,
    message: str,
) -> Dict[str, Any]:
    """Send a message to Jumbo with the full brand dossier pre-injected.

    Security:
      - brand_id UUID format validated by router before this is called
      - IDOR guard: .eq("user_id", user_id) on DB lookup
      - message length capped at 5000 chars by router
    """
    from app.deps import get_admin_client
    from app.services.tool_use_agents import run_tool_use_agent

    sb = get_admin_client()
    brand_row = (
        sb.table("personal_brands")
        .select("name, profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_row.data:
        raise ValueError(f"Brand {brand_id!r} not found for user {user_id!r}")

    brand_name = brand_row.data[0].get("name", "")
    profile = brand_row.data[0].get("profile_json") or {}

    trimmed = _trim_dossier(profile)
    dossier_json = _json.dumps(trimmed, indent=2, ensure_ascii=False)
    system_prompt = _JUMBO_CHAT_SYSTEM.format(dossier_json=dossier_json)

    result = run_tool_use_agent(
        agent_id="jumbo",
        task_type="brand_chat",
        system_prompt=system_prompt,
        user_prompt=f"CLIENT: {brand_name}\n\n{message}",
        user_id=user_id,
        brand_id=brand_id,
        available_tools=["web_search", "read_agent_training_docs"],
        temperature=0.7,
    )

    if not result.success:
        raise RuntimeError(f"Jumbo brand chat failed: {result.error}")

    return {"response": result.content, "brand_id": brand_id, "brand_name": brand_name}


def _trim_dossier(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Cap large lists and truncate long strings to keep system prompt manageable."""
    trimmed = dict(profile)
    for key in ("anxiety_list", "benefit_list", "first_week_angles",
                "relevance_topics", "power_words", "industry_lingo",
                "uvps", "metaphors", "content_pillars", "voice_adjectives"):
        if isinstance(trimmed.get(key), list):
            trimmed[key] = trimmed[key][:10]
    for key in ("emotional_pain_journal", "emotional_win_journal"):
        val = trimmed.get(key)
        if isinstance(val, str) and len(val) > 800:
            trimmed[key] = val[:800] + "..."
    if isinstance(trimmed.get("competitors"), list):
        trimmed["competitors"] = trimmed["competitors"][:3]
    bf = trimmed.get("belief_framework")
    if isinstance(bf, dict) and isinstance(bf.get("false_beliefs"), list):
        trimmed["belief_framework"] = {**bf, "false_beliefs": bf["false_beliefs"][:3]}
    if isinstance(trimmed.get("customer_segments"), list):
        trimmed["customer_segments"] = trimmed["customer_segments"][:3]
    return trimmed
