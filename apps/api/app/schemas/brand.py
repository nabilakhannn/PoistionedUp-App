"""Pydantic models for brand endpoints (ICA, Offer, Brand Statement)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── ICA (Ideal Client Avatar) ─────────────────────────────


class ICADemographics(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    income: Optional[str] = None
    location: Optional[str] = None
    education: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    marital_status: Optional[str] = None


class BuyingMotivations(BaseModel):
    money: Optional[str] = None
    time: Optional[str] = None
    performance: Optional[str] = None
    perception: Optional[str] = None


class PurchaseFears(BaseModel):
    anxiety: Optional[str] = None
    habits: Optional[str] = None
    inertia: Optional[str] = None
    switching_triggers: Optional[str] = None


class PainItem(BaseModel):
    pain: str = ""
    solutions: List[str] = Field(default_factory=list)


class DesireItem(BaseModel):
    desire: str = ""
    solutions: List[str] = Field(default_factory=list)


class NeedItem(BaseModel):
    need: str = ""
    solutions: List[str] = Field(default_factory=list)


class FearItem(BaseModel):
    fear: str = ""
    solutions: List[str] = Field(default_factory=list)


class ServiceFit(BaseModel):
    best_delivery: Optional[str] = None
    who_can_afford: Optional[str] = None


class ICAData(BaseModel):
    demographics: ICADemographics = Field(default_factory=ICADemographics)
    persona_words: List[str] = Field(default_factory=list)
    attract_clients: List[str] = Field(default_factory=list)
    red_flag_clients: List[str] = Field(default_factory=list)
    buying_motivations: BuyingMotivations = Field(default_factory=BuyingMotivations)
    service_fit: ServiceFit = Field(default_factory=ServiceFit)
    big_need: Optional[str] = None
    big_want: Optional[str] = None
    tried_before: Optional[str] = None
    buying_decision: Optional[str] = None
    if_nothing: Optional[str] = None
    purchase_fears: PurchaseFears = Field(default_factory=PurchaseFears)
    pains: List[PainItem] = Field(default_factory=list)
    desires: List[DesireItem] = Field(default_factory=list)
    needs: List[NeedItem] = Field(default_factory=list)
    fears: List[FearItem] = Field(default_factory=list)
    # Enhanced discovery fields (Slice 9)
    daily_frustrations: List[str] = Field(default_factory=list)
    dream_outcomes: List[str] = Field(default_factory=list)
    self_image: Optional[str] = None
    external_perception: Optional[str] = None
    biggest_fears: List[str] = Field(default_factory=list)
    peskiest_problems: List[str] = Field(default_factory=list)
    sales_call_link: Optional[str] = None
    discovery_questionnaire_link: Optional[str] = None


# ── Offer ──────────────────────────────────────────────────


class ObjectionItem(BaseModel):
    objection: str = ""
    response: str = ""


class OfferMarket(BaseModel):
    niche_statement: Optional[str] = None
    massive_pains: List[str] = Field(default_factory=list)
    purchasing_power: Optional[bool] = None
    leading_influencers: List[str] = Field(default_factory=list)
    competitor_offers: List[str] = Field(default_factory=list)


class OriginalDevice(BaseModel):
    name: str = ""
    description: str = ""


class OfferFramework(BaseModel):
    main_steps: List[str] = Field(default_factory=list)
    trifecta: List[str] = Field(default_factory=list)
    original_devices: List[OriginalDevice] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)


class OfferBoosters(BaseModel):
    urgency: Optional[str] = None
    bonuses: List[str] = Field(default_factory=list)
    guarantee: Optional[str] = None
    offer_name: Optional[str] = None


class ValueEquation(BaseModel):
    """Hormozi Value Equation: (Dream Outcome x Perceived Likelihood) / (Time Delay x Effort & Sacrifice)."""
    dream_outcome: Optional[str] = None
    perceived_likelihood: Optional[str] = None
    time_to_result: Optional[str] = None
    effort_required: Optional[str] = None


# ── Grand Slam Offer (Hormozi $100M Offers) ──────────────


class ProblemSolution(BaseModel):
    """A problem your prospect faces and how you solve it."""
    problem: str = ""
    solution: str = ""
    delivery_vehicle: Optional[str] = None  # "1:1", "small group", "1:many", "DIY", "DWY", "DFY"
    sexy_name: Optional[str] = None  # Hormozi: give each solution a compelling name


class GrandSlamEnhancers(BaseModel):
    """Hormozi's 4 offer enhancers: Scarcity, Urgency, Bonuses, Guarantees."""
    scarcity: Optional[str] = None  # Limited quantity / limited access
    urgency: Optional[str] = None  # Limited time / deadline
    bonuses: List[str] = Field(default_factory=list)  # Value-stacked bonuses with $ values
    guarantee_type: Optional[str] = None  # "unconditional", "conditional", "anti-guarantee", "implied"
    guarantee_statement: Optional[str] = None  # The actual guarantee wording
    offer_name: Optional[str] = None  # Hormozi naming formula


class GrandSlamOffer(BaseModel):
    """Alex Hormozi's $100M Offers Grand Slam framework."""
    starving_crowd: Optional[str] = None  # Who is desperate for this? (massive pain + purchasing power)
    dream_outcome_statement: Optional[str] = None  # The #1 dream result they want
    problems_solutions: List[ProblemSolution] = Field(default_factory=list)  # Problem→Solution→Delivery
    total_value: Optional[str] = None  # Sum of individual solution values ("$15,000+ value")
    price_anchor: Optional[str] = None  # What it would cost to solve this elsewhere
    actual_price: Optional[str] = None  # What you charge
    enhancers: GrandSlamEnhancers = Field(default_factory=GrandSlamEnhancers)


class MAGICMeasurable(BaseModel):
    quantifiable_outcome: Optional[str] = None
    milestones: List[str] = Field(default_factory=list)
    time_to_first_results: Optional[str] = None


class MAGICActionable(BaseModel):
    first_action: Optional[str] = None
    process_steps: List[str] = Field(default_factory=list)
    tools_and_resources: List[str] = Field(default_factory=list)


class MAGICGenerous(BaseModel):
    irresistible_reason: Optional[str] = None
    bonuses: List[str] = Field(default_factory=list)
    guarantee: Optional[str] = None


class MAGICScalable(BaseModel):
    delivery_model: Optional[str] = None
    systematized_parts: List[str] = Field(default_factory=list)
    max_clients: Optional[str] = None


class MAGICClear(BaseModel):
    one_sentence: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    why_you: Optional[str] = None
    cost_of_inaction: Optional[str] = None
    social_proof: Optional[str] = None
    price_justification: Optional[str] = None
    cta: Optional[str] = None


class MAGICFramework(BaseModel):
    measurable: MAGICMeasurable = Field(default_factory=MAGICMeasurable)
    actionable: MAGICActionable = Field(default_factory=MAGICActionable)
    generous: MAGICGenerous = Field(default_factory=MAGICGenerous)
    scalable: MAGICScalable = Field(default_factory=MAGICScalable)
    clear: MAGICClear = Field(default_factory=MAGICClear)


class OfferData(BaseModel):
    what: Optional[str] = None
    price: Optional[str] = None
    target_audience: Optional[str] = None
    why_it_matters: List[str] = Field(default_factory=list)
    how_it_works: List[str] = Field(default_factory=list)
    timeline: Optional[str] = None
    past_results: Optional[str] = None
    differentiator: Optional[str] = None
    first_move: Optional[str] = None
    objections: List[ObjectionItem] = Field(default_factory=list)
    market: OfferMarket = Field(default_factory=OfferMarket)
    framework: OfferFramework = Field(default_factory=OfferFramework)
    boosters: OfferBoosters = Field(default_factory=OfferBoosters)
    # MAGIC Offer Framework (Slice 9)
    magic: MAGICFramework = Field(default_factory=MAGICFramework)
    value_equation: ValueEquation = Field(default_factory=ValueEquation)
    offer_type: Optional[str] = None  # "timed", "transformation", or "logical"
    # Grand Slam Offer — Hormozi $100M Offers (Slice 9)
    grand_slam: GrandSlamOffer = Field(default_factory=GrandSlamOffer)


# ── Foundation ─────────────────────────────────────────────


class ITFactor(BaseModel):
    unfair_advantage: Optional[str] = None
    leverage_for_brand: Optional[str] = None
    leverage_for_niche: Optional[str] = None
    leverage_for_selling: Optional[str] = None
    leverage_for_network: Optional[str] = None


class FoundationData(BaseModel):
    """Stage 1: Who are you? Beliefs, IT Factor, achievements, stories."""
    beliefs: List[str] = Field(default_factory=list)
    it_factor: ITFactor = Field(default_factory=ITFactor)
    achievements_professional: List[str] = Field(default_factory=list)
    achievements_personal: List[str] = Field(default_factory=list)
    macro_story: Optional[str] = None
    micro_stories: List[str] = Field(default_factory=list)
    content_pillars: List[str] = Field(default_factory=list)


# ── Brand Statement ───────────────────────────────────────


class BrandData(BaseModel):
    statement: Optional[str] = None
    it_factor: ITFactor = Field(default_factory=ITFactor)
    content_pillars: List[str] = Field(default_factory=list)


# ── Complete Brand Profile ─────────────────────────────────


class BrandProfile(BaseModel):
    """Full brand profile (Foundation + ICA + Offer + Brand Statement)."""
    foundation: FoundationData = Field(default_factory=FoundationData)
    ica: ICAData = Field(default_factory=ICAData)
    offer: OfferData = Field(default_factory=OfferData)
    brand: BrandData = Field(default_factory=BrandData)


class BrandCompleteness(BaseModel):
    """Completion percentage for each brand module."""
    foundation_percent: int = 0
    ica_percent: int = 0
    offer_percent: int = 0
    brand_percent: int = 0
    authority_percent: int = 0
    messaging_percent: int = 0
    positioning_percent: int = 0
    competitors_percent: int = 0
    overall_percent: int = 0


# ── Chat Request/Response ──────────────────────────────────


class BrandChatRequest(BaseModel):
    """POST /brand/chat request body."""
    module: str = Field(..., pattern="^(foundation|ica|offer|brand|authority|messaging|positioning|competitors)$")
    message: str = Field(..., min_length=1, max_length=5000)
    brand_id: Optional[str] = Field(
        None,
        description="Personal brand ID to scope this chat to. If omitted, uses legacy profiles table.",
    )
    file_context: Optional[str] = Field(
        None,
        max_length=20000,
        description="Extracted text from an uploaded file, used as extra context for this message.",
    )
    file_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Original filename of the attached file.",
    )
    attachment_type: Optional[str] = Field(
        None,
        pattern="^(file|link|knowledge|inspo)$",
        description="Type of attachment: file, link, knowledge, or inspo. Controls stored badge icon.",
    )


class BrandChatResponse(BaseModel):
    """POST /brand/chat response."""
    reply: str
    extracted_so_far: Dict[str, Any] = Field(default_factory=dict)
    progress: float = 0.0
    chat_id: str


class BrandChatHistory(BaseModel):
    """GET /brand/chat/{module} response."""
    chat_id: Optional[str] = None
    module: str
    messages: List[Dict[str, str]] = Field(default_factory=list)
    extracted: Dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class BrandChatSummary(BaseModel):
    """One chat in the list."""
    chat_id: str
    module: str
    title: Optional[str] = None
    status: str
    message_count: int = 0
    created_at: str
    updated_at: str


class BrandChatListResponse(BaseModel):
    """GET /brand/chats/{module} — all chats for a module."""
    module: str
    chats: List[BrandChatSummary] = Field(default_factory=list)


class BrandChatCompleteResponse(BaseModel):
    """POST /brand/chat/{module}/complete response."""
    message: str
    merged_fields: int = 0


class BrandChatTitleRequest(BaseModel):
    """PATCH /brand/chat/{chat_id}/title."""
    title: str = Field(..., min_length=1, max_length=200)


# ── AI Suggest ─────────────────────────────────────────────


class BrandSuggestRequest(BaseModel):
    """POST /brand/suggest request body."""
    field: str = Field(..., min_length=1, description="Dot-path like 'ica.buying_motivations.money'")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current profile data for context",
    )


class BrandSuggestResponse(BaseModel):
    """POST /brand/suggest response."""
    field: str
    suggestion: str
