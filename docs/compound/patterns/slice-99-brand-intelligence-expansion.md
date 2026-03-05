# Slice 99 — Brand Intelligence Expansion (8-Section Framework Complete)

**Date:** March 2026
**Tests:** 20/20 passing
**TypeScript:** 0 errors
**Status:** COMPLETE

---

## What Was Built

Expanded the Brand Researcher agent from a 5-layer research system to a full **8-section intelligence framework**. The agent now produces a complete client dossier covering: Niche Market, Transformation (ZERO→DREAM), New Opportunity (UVPs + Tagline), Metaphors, Content Strategy, Your Story, Belief Framework, and Revenue Streams.

Added 15 new fields to `profile_json`, 5 new UI cards to the Brand Intelligence Report, and updated the agent's playbook and system prompt to instruct full 8-section research.

---

## Files Changed

| File | Change |
|------|--------|
| `apps/api/app/services/client_researcher.py` | Expanded `_BRAND_RESEARCHER_SYSTEM` with 5 new sections in output schema; updated `refresh_section()` allowed set; added 2 more search steps |
| `apps/api/app/services/playbooks.py` | Replaced 5-layer brand-researcher playbook with 8-section framework |
| `apps/web/src/lib/api/client-research.ts` | Added 9 new TypeScript interfaces + 15 new fields to `ClientDossier`; added 7 new values to `RefreshSection` type |
| `apps/web/src/components/brand-intelligence-report.tsx` | Added 6 new IntelCard sections (Transformation, New Opportunity, Metaphors, Your Story, Belief Framework, Power Words + Market Gap) |
| `apps/api/tests/test_slice99_brand_intelligence.py` | 20 new tests across 3 classes |
| `docs/compound/MASTER-SYSTEM-DESIGN.md` | Created permanent master design document |

---

## The 8-Section Framework (Design Pattern)

Each section maps to a specific output field in `profile_json`:

```
Section 1 — NICHE MARKET
  → content_pillars, voice_adjectives, ica_summary,
    market_gap, customer_segments, relevance_topics,
    power_words, industry_lingo

Section 2 — TRANSFORMATION
  → transformation: { zero_state, dream_state, journey }

Section 3 — NEW OPPORTUNITY
  → uvps: string[], tagline, niche_statement

Section 4 — METAPHORS
  → metaphors: string[]

Section 5 — CONTENT STRATEGY
  → content_pillars (shared with Section 1)

Section 6 — YOUR STORY
  → your_story: { background, growth_achievements, future_goals, mission }

Section 7 — BELIEF FRAMEWORK
  → belief_framework: {
      belief_statement: string,
      false_beliefs: [{ belief, counter_story }]
    }

Section 8 — REVENUE STREAMS
  → hormozi: { dream_outcome, perceived_likelihood, time_to_result,
               effort_sacrifice, guarantee, risk_reversals }
```

---

## New profile_json Fields (15 total added)

```json
{
  "transformation": {
    "zero_state": "...",
    "dream_state": "...",
    "journey": "..."
  },
  "uvps": ["...", "...", "..."],
  "tagline": "...",
  "niche_statement": "...",
  "metaphors": ["...", "...", "..."],
  "your_story": {
    "background": "...",
    "growth_achievements": "...",
    "future_goals": "...",
    "mission": "..."
  },
  "belief_framework": {
    "belief_statement": "...",
    "false_beliefs": [{"belief": "...", "counter_story": "..."}]
  },
  "market_gap": "...",
  "customer_segments": [{"segment": "...", "age": "...", "problem": "..."}],
  "relevance_topics": ["..."],
  "power_words": ["..."],
  "industry_lingo": ["..."]
}
```

---

## UI Pattern — Progressive Disclosure

New sections use `collapsible` IntelCards with `wide` (md:col-span-2) where content is rich:

- **Transformation** — `wide=true, collapsible=true` — two-column ZERO/DREAM layout + Journey below
- **New Opportunity** — tagline card with UVPs listed below
- **Metaphors** — numbered quote-style list
- **Your Story** — `wide=true, collapsible=true` — grid of background / achievements / mission
- **Belief Framework** — `wide=true, collapsible=true` — core belief box + false belief / counter-story pairs
- **Power Words + Market Gap** — combined card with badge chips for words / lingo

All new sections only render if data exists (`?.length ?? 0 > 0` or `?.field` checks), so existing brands without the new fields show no empty sections.

---

## refresh_section() Expansion Pattern

When adding new refreshable sections, update two places:

1. **Backend allowed set** in `refresh_section()`:
```python
allowed = {
    "hormozi", "competitors", ...,
    "transformation", "uvps", "metaphors",
    "your_story", "belief_framework", "power_words", "market_gap",
}
```

2. **Frontend type** in `client-research.ts`:
```typescript
export type RefreshSection =
  | "hormozi" | ...
  | "transformation" | "uvps" | "metaphors"
  | "your_story" | "belief_framework" | "power_words" | "market_gap";
```

---

## Security Check (OWASP)

- No new endpoints added — section expansion is purely in the agent system prompt and profile_json schema
- All refresh calls use existing `POST /client-research/refresh/{brand_id}` endpoint
- UUID guard on brand_id already in place (Slice 97)
- user_id scoping on all DB reads/writes already in place
- No new SSRF surfaces added

---

## Gap Analysis for Slice 100

Slice 99 closes GAP A (Brand Intelligence missing 5 of 8 sections). Now ready for:

- **GAP B: Offer Creator Agent** — reads complete 8-section dossier → generates Grand Slam Offer
- The `transformation`, `uvps`, `your_story`, `belief_framework`, and `metaphors` fields are exactly what the Offer Creator needs to write the offer headline, dream outcome, and guarantee sections
