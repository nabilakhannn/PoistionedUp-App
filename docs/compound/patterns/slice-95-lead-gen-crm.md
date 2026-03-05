# Slice 95 — Lead Gen CRM + Full Sales Room

**Date:** 2026-03-03
**Status:** Complete
**Tests:** 16/16 pass | 0 TS errors

---

## Problem

All 4 Sales room tabs were placeholder UI with "Slice 91/92" scaffolding badges. No backend data. The user's lead gen methodology (Cameron Sullivan / Outskill training) requires:
1. **Contact vs Lead**: contact = email only ($0 value). Lead = email + context = $200+ value.
2. **3 enrichment engines**: Personal LinkedIn posts + Company LinkedIn posts + Company website.
3. **7 enrichment fields** extracted by AI from those 3 sources.
4. **ICP = 3 layers**: Firmographics + Demographics + Psychographics.
5. **BANT scoring** (0-4): Budget + Authority + Need + Timing.
6. **Icebreaker**: 1-2 sentence opener referencing a specific lead fact.
7. **3-message sequence**: Day 1 Connect → Day 3 Value → Day 7 CTA → export to Instantly.ai.

---

## What Was Built

### Database: `leads` table (Migration 036)

```sql
leads (
  id UUID PK, user_id FK, brand_id UUID,
  full_name, title, company, linkedin_url, company_website, email, location, twitter_handle,
  status VARCHAR(50) DEFAULT 'cold',   -- cold | warm | hot | customer | disqualified
  enrichment JSONB DEFAULT '{}',       -- 7 enrichment fields
  bant_score INTEGER DEFAULT 0 CHECK (0-4),
  notes TEXT, transcript TEXT,         -- private — never exported
  icebreaker TEXT,
  outreach_draft JSONB DEFAULT '{}',   -- {linkedin_dm, cold_email: {subject, body}}
  sequence JSONB DEFAULT '[]',         -- [{label, day, channel, message, sent_at: null}]
  UNIQUE (user_id, brand_id, full_name, company)  -- dedup
)
```

### The 7 Enrichment Fields

| Field | Source | Engine |
|---|---|---|
| `professional_topics` | What they post/comment about | Personal LinkedIn |
| `recent_achievements` | Funding, promotions, launches (last 1-3 months) | Personal LinkedIn |
| `hiring_signals` | Is company growing/hiring? | Company LinkedIn |
| `pain_points` | Direct problem statements publicly admitted | Company LinkedIn |
| `company_changes` | Recent launches, rebrands, partnerships | Website |
| `industries_served` | Who their customers are | Website |
| `growth_signals` | Open roles, new offices, growth language | Website |

### Backend Services

**`lead_gen.py`** — 3 public functions:

1. `generate_leads_from_icp(brand_id, user_id, count)`: Reads 3 ICP layers from brand profile → Perplexity `sonar-pro` finds real professionals → Claude Haiku parses results.

2. `enrich_lead(lead)`:
   - Step 1: Perplexity → personal LinkedIn → fields 1-2
   - Step 2: Perplexity → company LinkedIn → fields 3-4
   - Step 3: `validate_url_for_fetch()` → httpx GET → Claude Haiku → fields 5-7
   - Step 4: Claude Sonnet scores BANT (0-4)

3. `generate_outreach(lead, enrichment, brand_profile)`: Claude Sonnet 4.6 with brand voice + transcript → returns `{icebreaker, outreach_draft, sequence[3 messages, sent_at:null]}`.

### API Endpoints (`/leads/*`)

```
GET    /leads                    list with brand_id + status filter
POST   /leads                    add single lead manually
POST   /leads/generate           AI-generate N leads from ICP (cap: 20)
POST   /leads/batch-enrich       enrich pasted list (cap: 3 — Vercel 60s limit)
POST   /leads/enrich/{id}        full 3-engine enrich + BANT
POST   /leads/outreach/{id}      generate icebreaker + DM + email + sequence
PATCH  /leads/{id}               update status/notes/transcript/icebreaker/sequence
DELETE /leads/{id}               remove lead
GET    /leads/export             .xlsx download (Instantly.ai-compatible)
```

### Newsletter Router (`/newsletter/*`)

```
GET  /newsletter/draft?brand_id=   latest draft from agent_deliverables (type=newsletter)
POST /newsletter/generate          Claude Sonnet → 400-600 word newsletter from research_brief
```

Reuses `agent_deliverables` table — no new DB table needed.

### Frontend Components

**`leads-crm.tsx`** — Table-first view (Apollo/Clay competitor analysis finding):
- Toolbar: Generate from ICP, Paste List, Add Lead, Export .xlsx, Table/Kanban toggle
- Filter bar: Status, BANT, Search
- Row hover actions: Enrich (with per-row spinner), → Outreach, Archive
- Bulk action bar (appears when ≥1 selected): Enrich All, Outreach, Export, Clear
- Empty state: 3 clear paths (Generate / Paste / Add)
- Lead detail panel (slide-in, 3 tabs):
  - **Profile**: 7 enrichment fields grouped by source (LinkedIn Personal / Company LinkedIn / Website) as chips. BANT dots. Re-enrich button.
  - **Transcript**: `<textarea>` with placeholder guidance. Re-generate outreach button.
  - **Outreach**: Editable icebreaker textarea (saves on blur via PATCH). LinkedIn DM + Cold Email with copy buttons. 3 sequence messages with labels + copy.

**`newsletter-engine.tsx`** — Loads existing draft on mount. Generate button → editable textarea. Copy to clipboard. Empty state with pipeline CTA.

**`outreach-queue.tsx`** — Derived view: filters leads where `outreach_draft` is non-empty. Two-column layout: LinkedIn DMs | Cold Emails. Copy buttons. Export to Instantly.ai.

**`sequences-tracker.tsx`** — Derived view: filters leads where `sequence` is non-empty. Table: Lead | Msg 1 | Msg 2 | Msg 3. Checkbox toggles `sent_at` between `null` and ISO timestamp via optimistic update + PATCH revert.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Table-first + Kanban toggle | Apollo/Clay both default to table. Kanban breaks at 50+ leads. |
| Batch cap at 3 leads | Vercel 60s limit. 3 leads × ~12s/lead = 36s safe margin. |
| BANT auto-scoring | Sorted DESC within column. 0-4 dots give instant outreach priority signal. |
| Icebreaker editable | User should manually review before sending (Cameron's recommendation). Saves on blur. |
| `sent_at` in sequence JSONB | Simple manual tracking. No outbox system needed. |
| Newsletter reuses `agent_deliverables` | Consistent with QA + Ad Creative. No new table. |
| Outreach/Sequences as derived views | Both read `leads` table. Zero DB overhead. |
| `.xlsx` export via `openpyxl` | Instantly.ai accepts .xlsx directly. ~500KB, well within Vercel 250MB limit. |
| Transcripts/notes never exported | OWASP A05 — user may paste sensitive call recordings or NDA-covered context. |

---

## Security

| OWASP | Check | Implementation |
|---|---|---|
| A01 IDOR | Only own leads | `.eq("user_id", user.id)` on all queries |
| A03 Injection | UUID + name sanitization | `_UUID_RE` on all IDs; `_SAFE_NAME_RE` strips `[^\w\s\-\.\,]` |
| A07 Auth | JWT required everywhere | `Depends(get_current_user)` |
| A10 SSRF | Company website fetch | `validate_url_for_fetch()` before any httpx call |
| A05 Data | No private data in export | Transcripts/notes NOT included in .xlsx |

---

## Files Changed

| File | Change |
|---|---|
| `infra/supabase/migrations/036_leads.sql` | NEW |
| `apps/api/app/services/lead_gen.py` | NEW |
| `apps/api/app/routers/leads.py` | NEW — 9 endpoints |
| `apps/api/app/routers/newsletter.py` | NEW — 2 endpoints |
| `apps/api/app/main.py` | Register leads + newsletter routers |
| `apps/api/requirements.txt` | Add openpyxl>=3.1.0 |
| `apps/web/src/lib/api/leads.ts` | NEW |
| `apps/web/src/lib/api/newsletter.ts` | NEW |
| `apps/web/src/components/leads-crm.tsx` | NEW |
| `apps/web/src/components/newsletter-engine.tsx` | NEW |
| `apps/web/src/components/outreach-queue.tsx` | NEW |
| `apps/web/src/components/sequences-tracker.tsx` | NEW |
| `apps/web/src/app/sales/page.tsx` | All 4 tabs replaced |
| `apps/api/tests/test_slice95_lead_gen.py` | NEW — 16 tests |

---

## E2E Verification

1. `pytest tests/test_slice95_lead_gen.py` → 16 pass ✅
2. `npx tsc --noEmit` → 0 errors ✅
3. Sales → **Leads** tab → table loads (no "Slice 91" badge)
4. "Generate from ICP" → up to 10 rows in Cold with BANT dots
5. Click lead → Profile tab → 7 enrichment fields shown by source group
6. Transcript tab → paste notes → "Re-generate outreach" → fresh icebreaker
7. Outreach tab → icebreaker is editable → edit → blur → saves via PATCH
8. Outreach tab → 3 sequence messages with labels + copy buttons
9. "Export .xlsx" → downloads file with icebreaker column (Instantly.ai ready)
10. Sales → **Newsletter** tab → "Generate" → 400-600 word draft → Copy works
11. Sales → **Outreach** tab → leads with outreach; grouped LinkedIn/Email; copy buttons
12. Sales → **Sequences** tab → per-lead tracker; checkbox marks sent; uncheck clears
13. No brand set → "Create a brand first" message (all tabs)
14. Empty ICP → Generate returns clear error + no crash

---

## Gap Identified (Next Actions)

- Slice 96: Universal Knowledge Dump System — extend `knowledge_documents` table with 4 columns; `knowledge_processor.py` service; `knowledge-dump.tsx` component replacing the static add-form in Intelligence room.
