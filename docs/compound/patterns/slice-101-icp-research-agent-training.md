# Slice 101: Gemini-Style Agent Training + ICP Research Pipeline

**Date:** 2026-03-04
**Status:** Complete
**Tests:** 12 new tests — 12/12 passing | 0 TS errors

---

## What Was Built

### 1. Gemini-Style `AgentTrainingPanel`
- **Instructions** section: large textarea that persists the agent's current plan/goals as a `doc_type: "instructions"` knowledge doc (`agent_scope: [agentId]`). One instructions doc per agent, auto-upserted.
- **Knowledge** card grid: Quick Note (auto-titles from first line), PDF/Doc upload, URL link. Docs display as thumbnail cards with type icon, title, delete button — matching the Gemini UI pattern.
- `doc_type: "instructions"` added to `VALID_DOC_TYPES` in `knowledge_docs.py` and `DocType` in `knowledge-docs.ts`.

### 2. Intelligence Page — Per-Agent Training
- Each agent card now has a `🎓 Train` button (top-right of card header)
- Clicking expands an inline `AgentTrainingPanel` at the bottom of the card with a dark `bg-[#0d1117]` background
- Only one agent expands at a time (`expandedAgent` state)

### 3. `IcpResearchPanel` (Sales → ICP Research tab)
4-stage pipeline mirroring the Sales Lead Research System Prompt Template:

| Stage | Name | What happens |
|-------|------|-------------|
| 1 | Objective | Auto-derived from brand profile — product, pricing, lead DB |
| 2 | Brand & Product Snapshot | Founder, mission, features, ideal outcome |
| 3 | Research Questions | Perplexity searches for ICP signals (industries, titles, pain points, regions) |
| 4 | Output / Apollo Filters | Company filters + Contact filters + Keywords/Tech + Apollo hint |

- Each stage card shows status badge: Pending / Running... / ✓ Complete
- Running stages show an animated indigo pulse dot
- Complete stages are clickable to expand/collapse result
- Stage 4 shows copy-able Apollo.io search hint + Apify scraper next step
- Optional overrides: product name, pricing
- Methodology reference collapsible at bottom

### 4. Backend: `research_icp()` + endpoints
- `apps/api/app/services/lead_gen.py` — `research_icp(brand_id, user_id, overrides)`:
  - Stages 1+2: pure brand profile extraction (fast, no AI)
  - Stage 3: Perplexity sonar-pro search → Claude Haiku extraction
  - Stage 4: structured Apollo filter generation
  - Graceful fallback to brand profile data if Perplexity unavailable
- `POST /leads/icp-research` — IDOR-safe (verifies brand belongs to user)
- `GET /leads/icp-methodology` — returns the ICP template text
- `ICP_METHODOLOGY` constant in `lead_gen.py` — the full 4-section template

### 5. Sales Page Restructure
- New first tab: **ICP Research** (🎯) — `IcpResearchPanel`
- Tab order: ICP Research → Leads → Outreach → Sequences → Newsletter
- Default tab changed from "leads" to "icp"

---

## Files Changed

| File | Change |
|------|--------|
| `apps/api/app/services/lead_gen.py` | Added `research_icp()`, `ICP_METHODOLOGY` constant |
| `apps/api/app/routers/leads.py` | Added `POST /leads/icp-research`, `GET /leads/icp-methodology`, `IcpResearchRequest` schema |
| `apps/api/app/routers/knowledge_docs.py` | Added "instructions" to `VALID_DOC_TYPES` |
| `apps/web/src/components/agent-training-panel.tsx` | Full Gemini-style rewrite |
| `apps/web/src/components/icp-research-panel.tsx` | New component (4-stage ICP pipeline) |
| `apps/web/src/app/intelligence/page.tsx` | Added `AgentTrainingPanel` import + `expandedAgent` state + Train button + inline expand |
| `apps/web/src/app/sales/page.tsx` | Added ICP tab as first tab, imported `IcpResearchPanel` |
| `apps/web/src/lib/api/leads.ts` | Added `icpResearch()` and `icpMethodology()` API methods |
| `apps/web/src/lib/api/knowledge-docs.ts` | Added "instructions" to `DocType` union |

---

## Security

- A01 IDOR: `research_icp()` verifies `brand_id` belongs to `user_id` via Supabase query
- A03 Injection: `_UUID_RE.match(brand_id)` in router before any DB access
- A07 Auth: `Depends(get_current_user)` on all new endpoints
- Knowledge docs: "instructions" type uses same user-scoped storage (no system scope leak)

---

## Verification

1. **Agent Training**: Go to Intelligence → click any agent's "🎓 Train" button → Instructions textarea + Knowledge card grid appear inline
2. **Save instructions**: Type goals in Instructions, click "Save Instructions" → persists as knowledge doc
3. **Add knowledge doc**: Click "Quick Note", paste text, Save → appears as card in grid
4. **ICP Research**: Go to Sales → ICP Research tab → click "Run ICP Research" → watch 4 stages animate to Complete
5. **Stage results**: Click a complete stage to expand → Stage 3 shows industries/titles/pain points → Stage 4 shows Apollo filter chips + copyable hint
