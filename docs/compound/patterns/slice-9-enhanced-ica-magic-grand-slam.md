# Slice 9: Enhanced ICA + MAGIC Offer + Grand Slam Offer

## Pattern: Dual Framework Offer Architecture

### Problem
Offer creation needs depth — users need both a structured framework (MAGIC) for clarity
AND a value-stacking framework (Hormozi Grand Slam) for pricing power. Single-framework
approaches leave gaps.

### Solution: Layered Offer Frameworks
Two complementary frameworks stored in the same `profile_json.offer` JSONB:

1. **MAGIC Offer Framework** (Graham) — 21 questions organized by letter:
   - M: Measurable outcomes, milestones, time to first results
   - A: Actionable first step, process steps, tools/resources
   - G: Generous value stack, bonuses, guarantee
   - I: Infinitely Scalable delivery model, systematized parts, max clients
   - C: Clear one-sentence pitch, before/after states, why-you, cost of inaction, social proof, CTA

2. **Grand Slam Offer** (Hormozi $100M Offers) — Problem→Solution→Delivery→Value:
   - Starving crowd identification (massive pain + purchasing power + easy to find)
   - Problems→Solutions list with delivery vehicles (1:1, small group, 1:many, DIY, DWY, DFY)
   - "Sexy names" for each solution (e.g. "The Never-Fall-Off Accountability System")
   - Value stacking: total value, price anchor (cost without you), actual price
   - Enhancers: Scarcity, Urgency, Bonuses (with $ values), Guarantee (4 types), Naming

3. **Hormozi Value Equation**: (Dream Outcome x Perceived Likelihood) / (Time Delay x Effort & Sacrifice)
   - Push to decrease the bottom (time + effort) rather than just increasing the top

### Schema Pattern: Nested Pydantic Models for Complex Frameworks

```python
# Each MAGIC letter gets its own model
class MAGICMeasurable(BaseModel):
    quantifiable_outcome: Optional[str] = None
    milestones: List[str] = Field(default_factory=list)
    time_to_first_results: Optional[str] = None

# Grand Slam uses Problem→Solution pairs
class ProblemSolution(BaseModel):
    problem: str = ""
    solution: str = ""
    delivery_vehicle: Optional[str] = None  # "1:1", "DWY", "DFY", etc.
    sexy_name: Optional[str] = None

# Enhancers model for Scarcity + Urgency + Bonuses + Guarantees + Naming
class GrandSlamEnhancers(BaseModel):
    scarcity: Optional[str] = None
    urgency: Optional[str] = None
    bonuses: List[str] = Field(default_factory=list)
    guarantee_type: Optional[str] = None  # 4 types
    guarantee_statement: Optional[str] = None
    offer_name: Optional[str] = None

# Composed into parent
class OfferData(BaseModel):
    magic: MAGICFramework = Field(default_factory=MAGICFramework)
    grand_slam: GrandSlamOffer = Field(default_factory=GrandSlamOffer)
    value_equation: ValueEquation = Field(default_factory=ValueEquation)
    offer_type: Optional[str] = None
```

**Key insight**: Deep merge with dot-notation (`grand_slam.enhancers.scarcity`) works
seamlessly through the existing `deep_merge()` function — no router changes needed.

### UI Pattern: Color-Coded Framework Sections

```tsx
// MAGIC: 5 color-coded sections (blue, green, yellow, purple, red) with letter badges
<MagicSection letter="M" title="Measurable" color="blue">

// Grand Slam: orange-themed section with $ badge
<div className="border-l-4 border-orange-500 bg-orange-50">

// Enhancers: amber-themed section with + badge
<div className="border-l-4 border-amber-500 bg-amber-50">
```

Visual grouping makes the complex offer page scannable. Each framework has
its own visual identity so users know which methodology they're working on.

### UI Pattern: ProblemSolutionList Component

A paired-input component with 4 fields per entry:
- Problem (text input)
- Solution (text input)
- Delivery method (select dropdown: 1:1, small group, 1:many, DIY, DWY, DFY)
- Sexy name (text input, optional)

Renders as cards with color-coded labels (red=problem, green=solution, orange=name).

### Enhanced ICA Pattern: Success Story Framework Depth

ICA chat questions push for depth:
- "Give me 10 peskiest problems" (not 3)
- "Give me 10 fears" (push for specifics)
- Identity gap: self-image vs external perception
- Red flag clients (who NOT to work with)
- Daily frustrations + dream outcomes
- Sales call recording link + discovery questionnaire link

### Chat Integration Pattern

Offer chat questions (15 total) flow through both frameworks:
1. Questions 1-11: MAGIC Framework (M→A→G→I→C)
2. Questions 12-14: Grand Slam Offer (starving crowd, problems→solutions, value stack)
3. Question 15: Value Equation + Offer Type

Extraction system prompt lists ALL valid fields from both frameworks.

### Completeness Calculation

Offer completeness now requires 11 fields (was 9):
```python
offer_pct = _section_completeness(offer, [
    "what", "price", "target_audience", "why_it_matters",
    "how_it_works", "timeline", "differentiator", "first_move",
    "objections", "magic", "grand_slam",
])
```

### Files Changed
- `apps/api/app/schemas/brand.py` — 10 new models (MAGIC + Grand Slam), 12 new fields on OfferData + ICAData
- `apps/api/app/services/brand_chat.py` — 15 offer questions, 12 ICA questions, extraction prompts, completeness
- `apps/web/src/app/brand/offer/page.tsx` — MAGIC sections, Grand Slam section, Enhancers, ProblemSolutionList
- `apps/web/src/app/brand/ica/page.tsx` — Enhanced fields, ListField, hints
- `apps/api/tests/test_brand.py` — 74 tests (was 49): +5 Enhanced ICA, +11 MAGIC, +9 Grand Slam

### Test Count
- Brand tests: 74 (was 49)
- All unit tests: 246 passed (integration tests need running server)

### Gotchas
- Python 3.9: use `Optional[str]` not `str | None`
- Nested MAGIC/Grand Slam fields work with existing `deep_merge()` via dot-notation
- No router changes needed — existing PATCH /offer handles new nested schema fields
- `_section_completeness` checks `isinstance(val, dict)` + any sub-value populated = counted
- Grand Slam `problems_solutions` is a List of ProblemSolution models (not simple strings)
- 4 guarantee types: unconditional, conditional, anti-guarantee, implied
- Offer page JS grew from 5.27kB to 6.87kB — still under 10kB threshold
