"""Tests for brand modules (Slices 7B + 8 + 9).

Unit tests for:
  - Brand schemas (Foundation, ICA, Offer, Brand validation)
  - Enhanced ICA fields (Slice 9): red flags, frustrations, fears, discovery links
  - MAGIC Offer Framework (Slice 9): measurable, actionable, generous, scalable, clear
  - Brand chat service (deep_merge, parse_chat_response, completeness, progress)
  - Opening messages for each module (including Foundation)
No external dependencies needed.
"""

import json
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env so app.config.settings can initialize
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Schema Tests ─────────────────────────────────────────────


class TestBrandSchemas:
    """Verify Pydantic models accept valid data and set defaults."""

    def test_ica_data_defaults(self):
        from app.schemas.brand import ICAData
        ica = ICAData()
        assert ica.demographics.name is None
        assert ica.persona_words == []
        assert ica.pains == []
        assert ica.buying_motivations.money is None

    def test_ica_data_with_values(self):
        from app.schemas.brand import ICAData
        ica = ICAData(
            big_need="Need leads",
            big_want="Authority and revenue",
            persona_words=["Extrovert", "Expert"],
        )
        assert ica.big_need == "Need leads"
        assert len(ica.persona_words) == 2

    def test_offer_data_defaults(self):
        from app.schemas.brand import OfferData
        offer = OfferData()
        assert offer.what is None
        assert offer.objections == []
        assert offer.market.niche_statement is None

    def test_offer_data_with_objections(self):
        from app.schemas.brand import OfferData, ObjectionItem
        offer = OfferData(
            what="LinkedIn branding service",
            price="$3000",
            objections=[
                ObjectionItem(
                    objection="Too expensive",
                    response="Compare to a full-time hire",
                ),
            ],
        )
        assert offer.what == "LinkedIn branding service"
        assert len(offer.objections) == 1
        assert offer.objections[0].objection == "Too expensive"

    def test_brand_data_defaults(self):
        from app.schemas.brand import BrandData
        brand = BrandData()
        assert brand.statement is None
        assert brand.content_pillars == []
        assert brand.it_factor.unfair_advantage is None

    def test_foundation_data_defaults(self):
        from app.schemas.brand import FoundationData
        f = FoundationData()
        assert f.beliefs == []
        assert f.it_factor.unfair_advantage is None
        assert f.achievements_professional == []
        assert f.achievements_personal == []
        assert f.macro_story is None
        assert f.micro_stories == []
        assert f.content_pillars == []

    def test_foundation_data_with_values(self):
        from app.schemas.brand import FoundationData
        f = FoundationData(
            beliefs=["LinkedIn advice is recycled", "Authority > followers"],
            achievements_professional=["Built $1M biz"],
            macro_story="Started broke, now here.",
            content_pillars=["Branding", "Growth", "AI"],
        )
        assert len(f.beliefs) == 2
        assert f.macro_story == "Started broke, now here."
        assert len(f.content_pillars) == 3

    def test_brand_profile_combines_all(self):
        from app.schemas.brand import BrandProfile
        profile = BrandProfile(
            foundation={"beliefs": ["Hot take"]},
            ica={"big_need": "Time"},
            offer={"what": "Service"},
            brand={"statement": "We help..."},
        )
        assert profile.foundation.beliefs == ["Hot take"]
        assert profile.ica.big_need == "Time"
        assert profile.offer.what == "Service"
        assert profile.brand.statement == "We help..."

    def test_brand_completeness_model(self):
        from app.schemas.brand import BrandCompleteness
        c = BrandCompleteness(
            foundation_percent=0, ica_percent=50,
            offer_percent=0, brand_percent=100, overall_percent=25,
        )
        assert c.ica_percent == 50
        assert c.foundation_percent == 0

    def test_chat_request_validates_module(self):
        from app.schemas.brand import BrandChatRequest
        req = BrandChatRequest(module="ica", message="Hello")
        assert req.module == "ica"

        req_f = BrandChatRequest(module="foundation", message="Hello")
        assert req_f.module == "foundation"

        with pytest.raises(Exception):
            BrandChatRequest(module="invalid", message="Hello")

    def test_chat_request_validates_message_length(self):
        from app.schemas.brand import BrandChatRequest
        with pytest.raises(Exception):
            BrandChatRequest(module="ica", message="")

    def test_suggest_request(self):
        from app.schemas.brand import BrandSuggestRequest
        req = BrandSuggestRequest(field="ica.buying_motivations.money")
        assert req.field == "ica.buying_motivations.money"
        assert req.context == {}


# ── Deep Merge Tests ─────────────────────────────────────────


class TestDeepMerge:
    """Verify deep_merge handles various nesting and dot-notation."""

    def test_simple_merge(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_overwrite_value(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_nested_merge(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge({"a": {"b": 1}}, {"a": {"c": 2}})
        assert result == {"a": {"b": 1, "c": 2}}

    def test_dot_notation(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge({}, {"demographics.age": 44})
        assert result == {"demographics": {"age": 44}}

    def test_dot_notation_preserves_existing(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge(
            {"demographics": {"name": "Sam"}},
            {"demographics.age": 44},
        )
        assert result["demographics"]["name"] == "Sam"
        assert result["demographics"]["age"] == 44

    def test_deep_dot_notation(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge({}, {"a.b.c": "deep"})
        assert result == {"a": {"b": {"c": "deep"}}}

    def test_array_replace(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge(
            {"tags": ["old"]},
            {"tags": ["new1", "new2"]},
        )
        assert result["tags"] == ["new1", "new2"]

    def test_empty_base(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge({}, {"key": "value"})
        assert result == {"key": "value"}

    def test_empty_updates(self):
        from app.services.brand_chat import deep_merge
        result = deep_merge({"key": "value"}, {})
        assert result == {"key": "value"}


# ── Parse Chat Response Tests ────────────────────────────────


class TestParseChatResponse:
    """Verify response parsing handles JSON, code fences, and fallbacks."""

    def test_valid_json(self):
        from app.services.brand_chat import parse_chat_response
        content = json.dumps({
            "reply": "Great! What's their occupation?",
            "extracted": {"demographics.occupation": "Tech founder"},
        })
        reply, extracted = parse_chat_response(content)
        assert reply == "Great! What's their occupation?"
        assert extracted["demographics.occupation"] == "Tech founder"

    def test_json_with_code_fences(self):
        from app.services.brand_chat import parse_chat_response
        content = "```json\n" + json.dumps({
            "reply": "Next question",
            "extracted": {"big_need": "Leads"},
        }) + "\n```"
        reply, extracted = parse_chat_response(content)
        assert reply == "Next question"
        assert extracted["big_need"] == "Leads"

    def test_invalid_json_falls_back(self):
        from app.services.brand_chat import parse_chat_response
        content = "This is just plain text, not JSON"
        reply, extracted = parse_chat_response(content)
        assert reply == "This is just plain text, not JSON"
        assert extracted == {}

    def test_json_without_extracted(self):
        from app.services.brand_chat import parse_chat_response
        content = json.dumps({"reply": "Tell me more"})
        reply, extracted = parse_chat_response(content)
        assert reply == "Tell me more"
        assert extracted == {}

    def test_empty_extracted(self):
        from app.services.brand_chat import parse_chat_response
        content = json.dumps({"reply": "Ok", "extracted": {}})
        reply, extracted = parse_chat_response(content)
        assert reply == "Ok"
        assert extracted == {}


# ── Completeness Tests ───────────────────────────────────────


class TestCompleteness:
    """Verify completeness calculation for brand modules."""

    def test_empty_profile(self):
        from app.services.brand_chat import calculate_completeness
        result = calculate_completeness({})
        assert result["foundation_percent"] == 0
        assert result["ica_percent"] == 0
        assert result["offer_percent"] == 0
        assert result["brand_percent"] == 0
        assert result["overall_percent"] == 0

    def test_partial_ica(self):
        from app.services.brand_chat import calculate_completeness
        result = calculate_completeness({
            "ica": {
                "demographics": {"name": "Sam", "age": 44},
                "persona_words": ["Extrovert"],
                "big_need": "Leads",
            }
        })
        assert result["ica_percent"] > 0
        assert result["offer_percent"] == 0

    def test_full_ica(self):
        from app.services.brand_chat import calculate_completeness
        result = calculate_completeness({
            "ica": {
                "demographics": {"name": "Sam", "age": 44},
                "persona_words": ["Extrovert", "Expert"],
                "buying_motivations": {"money": "Revenue", "time": "Busy"},
                "big_need": "Leads",
                "big_want": "Authority",
                "tried_before": "Courses",
                "if_nothing": "Miss out",
                "pains": [{"pain": "No time", "solutions": ["Outsource"]}],
                "desires": [{"desire": "Authority", "solutions": ["Content"]}],
                "red_flag_clients": ["No-shows", "Cheap clients"],
                "daily_frustrations": ["3 hours on content, 3 likes"],
                "peskiest_problems": ["Can't get consistent leads"],
            }
        })
        assert result["ica_percent"] == 100

    def test_overall_counts_modules_above_50(self):
        from app.services.brand_chat import calculate_completeness
        result = calculate_completeness({
            "ica": {
                "demographics": {"name": "Sam"},
                "persona_words": ["Expert"],
                "buying_motivations": {"money": "Revenue"},
                "big_need": "Leads",
                "big_want": "Authority",
                "tried_before": "Courses",
                "if_nothing": "Miss out",
                "pains": [{"pain": "No time"}],
                "desires": [{"desire": "Authority"}],
                "red_flag_clients": ["Cheap clients"],
                "daily_frustrations": ["Content takes too long"],
                "peskiest_problems": ["No leads"],
            },
            "brand": {
                "statement": "We help...",
                "it_factor": {"unfair_advantage": "Lost 20kg"},
                "content_pillars": ["Branding", "Growth"],
            },
        })
        # Foundation: 0%, ICA: 100%, Offer: 0%, Brand: 100%
        # 2 of 4 modules >= 50% -> overall = 50%
        assert result["overall_percent"] == 50

    def test_foundation_completeness(self):
        from app.services.brand_chat import calculate_completeness
        result = calculate_completeness({
            "foundation": {
                "beliefs": ["Hot take 1", "Hot take 2"],
                "it_factor": {"unfair_advantage": "Lost 20kg"},
                "achievements_professional": ["Built $1M biz"],
                "achievements_personal": ["Grew up broke"],
                "macro_story": "From zero to here.",
                "content_pillars": ["Branding", "Growth"],
            },
        })
        assert result["foundation_percent"] == 100


# ── Progress Estimation Tests ────────────────────────────────


class TestProgressEstimation:
    """Verify chat progress estimation."""

    def test_empty_extracted(self):
        from app.services.brand_chat import estimate_progress
        assert estimate_progress("ica", {}) == 0.0

    def test_some_extracted(self):
        from app.services.brand_chat import estimate_progress
        progress = estimate_progress("ica", {
            "demographics": {"name": "Sam", "age": 44},
            "big_need": "Leads",
        })
        assert progress > 0.0
        assert progress < 1.0

    def test_capped_at_one(self):
        from app.services.brand_chat import estimate_progress
        # Lots of fields should cap at 1.0
        big_extracted = {f"field_{i}": f"value_{i}" for i in range(50)}
        progress = estimate_progress("ica", big_extracted)
        assert progress == 1.0


# ── Opening Message Tests ────────────────────────────────────


class TestOpeningMessages:
    """Verify each module has an opening question."""

    def test_ica_opening(self):
        from app.services.brand_chat import get_opening_message
        msg = get_opening_message("ica")
        assert "dream client" in msg
        assert len(msg) > 20

    def test_offer_opening(self):
        from app.services.brand_chat import get_opening_message
        msg = get_opening_message("offer")
        assert "result" in msg.lower()
        assert "measurable" in msg.lower()
        assert len(msg) > 20

    def test_brand_opening(self):
        from app.services.brand_chat import get_opening_message
        msg = get_opening_message("brand")
        # Opening asks user to fill in the brand positioning statement
        assert "i help" in msg.lower()
        assert len(msg) > 20

    def test_foundation_opening(self):
        from app.services.brand_chat import get_opening_message
        msg = get_opening_message("foundation")
        assert "foundation" in msg.lower() or "brand" in msg.lower() or "believe" in msg.lower()
        assert len(msg) > 20

    def test_unknown_module_fallback(self):
        from app.services.brand_chat import get_opening_message
        msg = get_opening_message("unknown")
        assert len(msg) > 0


# ── Build Chat Messages Tests ────────────────────────────────


class TestBuildChatMessages:
    """Verify LLM message building."""

    def test_includes_system_prompt(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("ica", [])
        assert messages[0]["role"] == "system"
        assert "Ideal Client Avatar" in messages[0]["content"]

    def test_includes_conversation(self):
        from app.services.brand_chat import build_chat_messages
        conversation = [
            {"role": "assistant", "content": "What's their job?"},
            {"role": "user", "content": "Tech founders"},
        ]
        messages = build_chat_messages("ica", conversation)
        assert len(messages) == 3  # system + 2 conversation
        assert messages[1]["content"] == "What's their job?"
        assert messages[2]["content"] == "Tech founders"

    def test_offer_system_prompt(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("offer", [])
        assert "offer" in messages[0]["content"].lower()

    def test_brand_system_prompt(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("brand", [])
        assert "brand" in messages[0]["content"].lower()


# ── Module Questions Tests ───────────────────────────────────


class TestModuleQuestions:
    """Verify each module has enough questions for a full discovery."""

    def test_ica_has_enough_questions(self):
        from app.services.brand_chat import MODULE_QUESTIONS
        assert len(MODULE_QUESTIONS["ica"]) >= 8

    def test_offer_has_enough_questions(self):
        from app.services.brand_chat import MODULE_QUESTIONS
        assert len(MODULE_QUESTIONS["offer"]) >= 8

    def test_brand_has_enough_questions(self):
        from app.services.brand_chat import MODULE_QUESTIONS
        assert len(MODULE_QUESTIONS["brand"]) >= 3

    def test_foundation_has_enough_questions(self):
        from app.services.brand_chat import MODULE_QUESTIONS
        assert len(MODULE_QUESTIONS["foundation"]) >= 8

    def test_foundation_system_prompt(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("foundation", [])
        assert messages[0]["role"] == "system"
        assert "foundation" in messages[0]["content"].lower() or "branding" in messages[0]["content"].lower()

    def test_foundation_progress(self):
        from app.services.brand_chat import estimate_progress
        progress = estimate_progress("foundation", {
            "beliefs": ["Hot take"],
            "it_factor": {"unfair_advantage": "Lost 20kg"},
            "macro_story": "From zero to here",
        })
        assert progress > 0.0
        assert progress < 1.0


# ── Enhanced ICA Tests (Slice 9) ────────────────────────────


class TestEnhancedICA:
    """Verify enhanced ICA schema fields from Slice 9."""

    def test_ica_enhanced_defaults(self):
        from app.schemas.brand import ICAData
        ica = ICAData()
        assert ica.daily_frustrations == []
        assert ica.dream_outcomes == []
        assert ica.self_image is None
        assert ica.external_perception is None
        assert ica.biggest_fears == []
        assert ica.peskiest_problems == []
        assert ica.sales_call_link is None
        assert ica.discovery_questionnaire_link is None

    def test_ica_enhanced_with_values(self):
        from app.schemas.brand import ICAData
        ica = ICAData(
            daily_frustrations=["3 hours on content, 3 likes"],
            dream_outcomes=["Wake up to inbound leads"],
            self_image="I'm good at what I do but nobody knows",
            external_perception="Just another consultant",
            biggest_fears=["Being irrelevant"],
            peskiest_problems=["Can't get consistent leads"],
            sales_call_link="https://zoom.us/rec/123",
            discovery_questionnaire_link="https://forms.google.com/abc",
        )
        assert len(ica.daily_frustrations) == 1
        assert ica.self_image is not None
        assert ica.sales_call_link == "https://zoom.us/rec/123"

    def test_ica_red_flag_clients(self):
        from app.schemas.brand import ICAData
        ica = ICAData(
            attract_clients=["Ambitious founders", "Fast movers"],
            red_flag_clients=["Tire-kickers", "Micromanagers"],
        )
        assert len(ica.attract_clients) == 2
        assert len(ica.red_flag_clients) == 2

    def test_ica_enhanced_questions_count(self):
        from app.services.brand_chat import MODULE_QUESTIONS
        # Enhanced ICA should have 12 questions (up from 10)
        assert len(MODULE_QUESTIONS["ica"]) >= 12

    def test_ica_enhanced_system_prompt_fields(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("ica", [])
        system = messages[0]["content"]
        assert "daily_frustrations" in system
        assert "peskiest_problems" in system
        assert "biggest_fears" in system


# ── MAGIC Offer Framework Tests (Slice 9) ────────────────────


class TestMAGICOfferFramework:
    """Verify MAGIC Offer Framework schema and chat integration."""

    def test_magic_framework_defaults(self):
        from app.schemas.brand import MAGICFramework
        m = MAGICFramework()
        assert m.measurable.quantifiable_outcome is None
        assert m.measurable.milestones == []
        assert m.actionable.first_action is None
        assert m.actionable.process_steps == []
        assert m.generous.guarantee is None
        assert m.generous.bonuses == []
        assert m.scalable.delivery_model is None
        assert m.clear.one_sentence is None
        assert m.clear.before_state is None
        assert m.clear.after_state is None

    def test_magic_measurable(self):
        from app.schemas.brand import MAGICMeasurable
        m = MAGICMeasurable(
            quantifiable_outcome="Add $10K MRR in 90 days",
            milestones=["Week 2: Foundation done", "Week 4: First post"],
            time_to_first_results="2 weeks",
        )
        assert m.quantifiable_outcome == "Add $10K MRR in 90 days"
        assert len(m.milestones) == 2

    def test_magic_actionable(self):
        from app.schemas.brand import MAGICActionable
        a = MAGICActionable(
            first_action="60-min brand discovery call",
            process_steps=["Step 1: Discovery", "Step 2: Build"],
            tools_and_resources=["Brand doc", "Calendar template"],
        )
        assert a.first_action == "60-min brand discovery call"
        assert len(a.tools_and_resources) == 2

    def test_magic_generous(self):
        from app.schemas.brand import MAGICGenerous
        g = MAGICGenerous(
            irresistible_reason="$50K value for $5K investment",
            bonuses=["Hook library", "Content calendar"],
            guarantee="Full refund if no results in 90 days",
        )
        assert len(g.bonuses) == 2
        assert "refund" in g.guarantee.lower()

    def test_magic_scalable(self):
        from app.schemas.brand import MAGICScalable
        s = MAGICScalable(
            delivery_model="Hybrid: group coaching + 1:1 calls",
            systematized_parts=["Onboarding email", "Content templates"],
            max_clients="20 per cohort",
        )
        assert "hybrid" in s.delivery_model.lower()

    def test_magic_clear(self):
        from app.schemas.brand import MAGICClear
        c = MAGICClear(
            one_sentence="I help B2B founders build authority on LinkedIn in 90 days",
            before_state="Invisible on LinkedIn, zero leads",
            after_state="Recognized authority, 5 inbound leads/week",
            why_you="I've done it myself + 50 clients",
            cost_of_inaction="Stay invisible for another year",
            social_proof="50 clients, $2M revenue generated",
            price_justification="One client covers the investment 10x",
            cta="Book a discovery call",
        )
        assert c.one_sentence is not None
        assert c.before_state is not None
        assert c.after_state is not None

    def test_offer_data_includes_magic(self):
        from app.schemas.brand import OfferData
        offer = OfferData(
            what="LinkedIn branding",
            magic={
                "measurable": {"quantifiable_outcome": "$10K MRR"},
                "clear": {"one_sentence": "I help founders..."},
            },
            value_equation={"dream_outcome": "Authority + revenue"},
            offer_type="transformation",
        )
        assert offer.magic.measurable.quantifiable_outcome == "$10K MRR"
        assert offer.magic.clear.one_sentence == "I help founders..."
        assert offer.value_equation.dream_outcome == "Authority + revenue"
        assert offer.offer_type == "transformation"

    def test_value_equation_defaults(self):
        from app.schemas.brand import ValueEquation
        v = ValueEquation()
        assert v.dream_outcome is None
        assert v.perceived_likelihood is None
        assert v.time_to_result is None
        assert v.effort_required is None

    def test_offer_questions_cover_magic(self):
        from app.services.brand_chat import MODULE_QUESTIONS
        questions = MODULE_QUESTIONS["offer"]
        all_text = " ".join(questions).lower()
        # M - Measurable: explicit keyword in first question
        assert "measurable" in all_text
        # A - Actionable: asks about first steps and exact process
        assert "first thing" in all_text or "exact steps" in all_text
        # G - Generous: asks about bonuses and risk elimination
        assert "bonuses" in all_text or "guarantee" in all_text
        # I - Infinitely Scalable: asks about automation and time leverage
        assert "automated" in all_text or "without trading" in all_text
        # C - Clear: asks if offer fits in one sentence
        assert "one sentence" in all_text or "understand your offer" in all_text

    def test_offer_system_prompt_has_magic_fields(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("offer", [])
        system = messages[0]["content"]
        assert "magic.measurable" in system
        assert "magic.clear" in system
        assert "value_equation" in system

    def test_offer_completeness_includes_magic(self):
        from app.services.brand_chat import calculate_completeness
        result = calculate_completeness({
            "offer": {
                "what": "LinkedIn branding",
                "price": "$5000",
                "target_audience": "B2B founders",
                "why_it_matters": ["Authority"],
                "how_it_works": ["Step 1"],
                "timeline": "90 days",
                "differentiator": "Done it myself",
                "first_move": "Book a call",
                "objections": [{"objection": "Price", "response": "ROI"}],
                "magic": {
                    "measurable": {"quantifiable_outcome": "$10K MRR"},
                    "clear": {"one_sentence": "I help..."},
                },
                "grand_slam": {
                    "starving_crowd": "Coaches who just quit corporate",
                },
            }
        })
        assert result["offer_percent"] == 100


# ── Grand Slam Offer Tests (Hormozi $100M Offers) ───────────


class TestGrandSlamOffer:
    """Verify Hormozi Grand Slam Offer schema and chat integration."""

    def test_grand_slam_defaults(self):
        from app.schemas.brand import GrandSlamOffer
        gs = GrandSlamOffer()
        assert gs.starving_crowd is None
        assert gs.dream_outcome_statement is None
        assert gs.problems_solutions == []
        assert gs.total_value is None
        assert gs.price_anchor is None
        assert gs.actual_price is None
        assert gs.enhancers.scarcity is None
        assert gs.enhancers.urgency is None
        assert gs.enhancers.bonuses == []
        assert gs.enhancers.guarantee_type is None
        assert gs.enhancers.guarantee_statement is None
        assert gs.enhancers.offer_name is None

    def test_grand_slam_with_values(self):
        from app.schemas.brand import GrandSlamOffer
        gs = GrandSlamOffer(
            starving_crowd="Coaches who just quit corporate",
            dream_outcome_statement="$10K/month within 90 days",
            total_value="$25,000+",
            price_anchor="$50,000 (agency + coaching)",
            actual_price="$5,000",
        )
        assert gs.starving_crowd == "Coaches who just quit corporate"
        assert gs.actual_price == "$5,000"

    def test_problem_solution_model(self):
        from app.schemas.brand import ProblemSolution
        ps = ProblemSolution(
            problem="Don't know what to post",
            solution="Content strategy with pillar system",
            delivery_vehicle="DWY",
            sexy_name="The Viral Content Blueprint",
        )
        assert ps.problem == "Don't know what to post"
        assert ps.sexy_name == "The Viral Content Blueprint"
        assert ps.delivery_vehicle == "DWY"

    def test_grand_slam_problems_solutions_list(self):
        from app.schemas.brand import GrandSlamOffer
        gs = GrandSlamOffer(
            problems_solutions=[
                {"problem": "No brand identity", "solution": "Brand foundation workshop", "sexy_name": "The Identity Forge"},
                {"problem": "No content ideas", "solution": "AI idea generator", "delivery_vehicle": "1:many"},
                {"problem": "Bad hooks", "solution": "Hook library + training", "sexy_name": "The Hook Arsenal"},
            ]
        )
        assert len(gs.problems_solutions) == 3
        assert gs.problems_solutions[0].sexy_name == "The Identity Forge"
        assert gs.problems_solutions[1].delivery_vehicle == "1:many"

    def test_grand_slam_enhancers(self):
        from app.schemas.brand import GrandSlamEnhancers
        e = GrandSlamEnhancers(
            scarcity="Only 10 spots per cohort",
            urgency="Doors close Friday at midnight",
            bonuses=["Hook Library ($997 value)", "Content Calendar ($497 value)"],
            guarantee_type="conditional",
            guarantee_statement="If you don't get 5 qualified leads in 30 days, I'll work with you for free until you do",
            offer_name="The Authority Accelerator",
        )
        assert e.scarcity == "Only 10 spots per cohort"
        assert len(e.bonuses) == 2
        assert e.guarantee_type == "conditional"
        assert e.offer_name == "The Authority Accelerator"

    def test_offer_data_includes_grand_slam(self):
        from app.schemas.brand import OfferData
        offer = OfferData(
            what="LinkedIn branding",
            grand_slam={
                "starving_crowd": "B2B coaches",
                "problems_solutions": [
                    {"problem": "No brand", "solution": "Foundation workshop"},
                ],
                "enhancers": {
                    "scarcity": "10 spots",
                    "guarantee_type": "unconditional",
                },
            },
        )
        assert offer.grand_slam.starving_crowd == "B2B coaches"
        assert len(offer.grand_slam.problems_solutions) == 1
        assert offer.grand_slam.enhancers.scarcity == "10 spots"

    def test_offer_questions_cover_grand_slam(self):
        from app.services.brand_chat import MODULE_QUESTIONS
        questions = MODULE_QUESTIONS["offer"]
        all_text = " ".join(questions).lower()
        # Grand Slam concepts from Hormozi's $100M Offers framework
        assert "starving crowd" in all_text
        assert "every problem" in all_text or "list every problem" in all_text
        assert "name that sells" in all_text
        assert "value equation" in all_text or "dream outcome" in all_text

    def test_offer_system_prompt_has_grand_slam_fields(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("offer", [])
        system = messages[0]["content"]
        assert "grand_slam" in system
        assert "starving_crowd" in system
        assert "problems_solutions" in system
        assert "enhancers" in system

    def test_offer_completeness_includes_grand_slam(self):
        from app.services.brand_chat import calculate_completeness
        result = calculate_completeness({
            "offer": {
                "what": "LinkedIn branding",
                "price": "$5000",
                "target_audience": "B2B founders",
                "why_it_matters": ["Authority"],
                "how_it_works": ["Step 1"],
                "timeline": "90 days",
                "differentiator": "Done it myself",
                "first_move": "Book a call",
                "objections": [{"objection": "Price", "response": "ROI"}],
                "magic": {"measurable": {"quantifiable_outcome": "$10K"}},
                "grand_slam": {"starving_crowd": "B2B coaches"},
            }
        })
        assert result["offer_percent"] == 100


# ── File Attachment Tests (Slice 19) ─────────────────────────


class TestFileAttachmentSchema:
    """Verify BrandChatRequest accepts optional file fields."""

    def test_chat_request_without_file(self):
        from app.schemas.brand import BrandChatRequest
        req = BrandChatRequest(module="foundation", message="Hello")
        assert req.file_context is None
        assert req.file_name is None

    def test_chat_request_with_file_context(self):
        from app.schemas.brand import BrandChatRequest
        req = BrandChatRequest(
            module="ica",
            message="Here is my background",
            file_context="I am a fitness coach with 10 years experience.",
            file_name="bio.txt",
        )
        assert req.file_context == "I am a fitness coach with 10 years experience."
        assert req.file_name == "bio.txt"

    def test_chat_request_file_context_max_length(self):
        from app.schemas.brand import BrandChatRequest
        # Should accept up to 20000 chars
        long_text = "x" * 20000
        req = BrandChatRequest(
            module="foundation",
            message="test",
            file_context=long_text,
        )
        assert len(req.file_context) == 20000

        # Over 20000 should fail
        with pytest.raises(Exception):
            BrandChatRequest(
                module="foundation",
                message="test",
                file_context="x" * 20001,
            )


class TestFileUploadEndpoint:
    """Test POST /brand/chat/upload-context endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client with auth dependency overridden."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import CurrentUser, get_current_user

        mock_user = CurrentUser(id="test-user-id", email="test@example.com")
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_upload_txt_file(self, client):
        """Should extract text from a .txt file."""
        import io
        content = b"I have been a fitness coach for 10 years. I specialize in strength training."
        resp = client.post(
            "/brand/chat/upload-context",
            files={"file": ("bio.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "bio.txt"
        assert data["chars_extracted"] > 0
        assert "fitness coach" in data["text"]
        assert data["truncated"] is False

    def test_upload_csv_file(self, client):
        """Should extract text from a .csv file."""
        import io
        csv_content = b"name,expertise\nJohn,Marketing\nJane,Design"
        resp = client.post(
            "/brand/chat/upload-context",
            files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Marketing" in data["text"]

    def test_upload_rejects_unsupported_type(self, client):
        """Should reject files with unsupported extensions."""
        import io
        resp = client.post(
            "/brand/chat/upload-context",
            files={"file": ("virus.exe", io.BytesIO(b"bad"), "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_upload_rejects_empty_file(self, client):
        """Should reject empty files."""
        import io
        resp = client.post(
            "/brand/chat/upload-context",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_upload_accepts_image_extensions(self, client):
        """Should accept image files (.png, .jpg, etc.) without erroring on extension."""
        import io
        # We send a tiny PNG (not a real image, but checks extension validation passes)
        # The actual Vision OCR will fail on invalid image, but we test the route accepts it
        resp = client.post(
            "/brand/chat/upload-context",
            files={"file": ("screenshot.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimage"), "image/png")},
        )
        # 200 if Vision OCR works, 422 if it fails to extract (both fine, not 400)
        assert resp.status_code in (200, 422)

    def test_upload_accepts_jpg(self, client):
        """Should accept .jpg files."""
        import io
        resp = client.post(
            "/brand/chat/upload-context",
            files={"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff\xe0fake"), "image/jpeg")},
        )
        assert resp.status_code in (200, 422)

    def test_upload_endpoint_requires_auth(self):
        """Without auth override, should require authentication."""
        from fastapi.testclient import TestClient
        from app.main import app
        import io
        # No dependency override, so auth should be enforced
        with TestClient(app) as c:
            resp = c.post(
                "/brand/chat/upload-context",
                files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
            )
            assert resp.status_code == 401


class TestPDFExtraction:
    """Test the multi-tier PDF text extraction (pypdf + PyMuPDF fallback)."""

    def test_extract_text_from_pdf_basic(self):
        """Should extract text from a standard text-based PDF."""
        from app.services.ingestion import extract_text_from_pdf

        # Create a minimal valid PDF with text
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            b"4 0 obj << /Length 64 >>\nstream\n"
            b"BT /F1 12 Tf 72 700 Td (My personal brand is about executive coaching) Tj ET\n"
            b"endstream\nendobj\n"
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
            b"0000000115 00000 n \n0000000266 00000 n \n0000000380 00000 n \n"
            b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n449\n%%EOF"
        )
        text = extract_text_from_pdf(pdf_bytes)
        assert "executive coaching" in text.lower()

    def test_extract_text_from_pdf_pymupdf_fallback(self):
        """PyMuPDF-generated PDFs should extract via fallback when pypdf returns little."""
        import fitz

        # Create a PDF with PyMuPDF that uses its built-in fonts
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "Brand strategy for tech founders", fontsize=14)
        page.insert_text((72, 130), "I help startup CEOs build executive presence", fontsize=11)
        pdf_bytes = doc.tobytes()
        doc.close()

        from app.services.ingestion import extract_text_from_pdf
        text = extract_text_from_pdf(pdf_bytes)
        assert "brand strategy" in text.lower() or "tech founders" in text.lower()
        assert len(text.strip()) > 20

    def test_upload_pdf_file(self):
        """POST /brand/chat/upload-context should extract text from a real PDF."""
        import io
        import fitz
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import CurrentUser, get_current_user

        mock_user = CurrentUser(id="test-user-id", email="test@example.com")
        app.dependency_overrides[get_current_user] = lambda: mock_user

        # Create a real PDF with PyMuPDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "My coaching methodology overview", fontsize=14)
        page.insert_text((72, 130), "I work with Fortune 500 executives on leadership development", fontsize=11)
        pdf_bytes = doc.tobytes()
        doc.close()

        client = TestClient(app)
        resp = client.post(
            "/brand/chat/upload-context",
            files={"file": ("coaching_method.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "coaching_method.pdf"
        assert data["chars_extracted"] > 20
        # Should contain the actual text from the PDF
        text_lower = data["text"].lower()
        assert "coaching" in text_lower or "leadership" in text_lower or "executive" in text_lower
        app.dependency_overrides.clear()

    def test_extract_text_routes_pdf_by_filename(self):
        """extract_text should detect PDF by filename even if content_type is wrong."""
        import fitz
        from app.services.ingestion import extract_text

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "Content pillars for personal branding", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()

        # Pass wrong content_type, but correct filename
        text = extract_text(pdf_bytes, "application/octet-stream", "brand_pillars.pdf")
        assert "content pillars" in text.lower() or "personal branding" in text.lower()


class TestLinkExtractionEndpoint:
    """Test POST /brand/chat/extract-link endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client with auth dependency overridden."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import CurrentUser, get_current_user

        mock_user = CurrentUser(id="test-user-id", email="test@example.com")
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_link_endpoint_exists(self, client):
        """POST /brand/chat/extract-link should not return 404."""
        resp = client.post(
            "/brand/chat/extract-link",
            json={"url": "https://example.com"},
        )
        # 200 if extraction works, 422 if it fails, both fine, not 404
        assert resp.status_code in (200, 422)

    def test_link_endpoint_requires_url(self, client):
        """Should return 400 if URL is missing."""
        resp = client.post("/brand/chat/extract-link", json={"url": ""})
        assert resp.status_code == 400

    def test_link_endpoint_requires_auth(self):
        """Without auth override, should require authentication."""
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            resp = c.post(
                "/brand/chat/extract-link",
                json={"url": "https://example.com"},
            )
            assert resp.status_code == 401
