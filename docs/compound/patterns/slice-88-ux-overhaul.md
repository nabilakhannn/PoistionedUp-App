# Slice 88: UX Overhaul — Onboarding + Home Inbox + 5-Tab Nav

**Date:** 2026-03-03
**Status:** Shipped
**Tests:** 18/18

---

## Problem

New users landed on a 11-tab technical dashboard with no guidance. The most important daily action (approving content for posting) was buried 3 clicks deep inside the Deliverables panel. There was no user journey from sign-up to first approved post.

---

## Solution

Rebuilt the Mission Control UX around one question: **"What do I need to do right now?"**

### User Journey (after this slice)

```
First visit (no brands yet)
    ↓
/onboarding  (4 steps, ~5 min)
  Step 1: Who are you?      → POST /brands
  Step 2: Your voice        → paste 3 posts → PATCH /brands/{id}/foundation
  Step 3: Connect Telegram  → @Jumbohere_bot deep-link (skippable)
  Step 4: You're all set    → sets localStorage + CTA to Mission Control
    ↓
/mission-control  (Home — redesigned)
  • Needs your approval  ← primary action
  • 7-day content strip  ← what's coming up
  • Agent status         ← what's happening
  • Latest from Jumbo    ← morning briefing
  + Floating "+" on every MC page
```

---

## Navigation Change

**Before:** 11 technical tabs (Dashboard, Analytics, Orchestrator, Gateway, Agent Chat, Goals, Competitors, QA, Playbooks, Ledger, Settings)

**After:** 5 user-friendly tabs

| Tab | href | Contains |
|-----|------|---------|
| **Home** | `/mission-control` | Approval inbox + 7-day strip + agents + briefing |
| **Content** | `/mission-control/content` | Pipeline + trending + queue |
| **My Team** | `/mission-control/orchestrator` | Agent roster + goals + chat |
| **Results** | `/mission-control/analytics` | Analytics + competitors |
| **Settings** | `/mission-control/settings` | Connectors + Playbooks + History + System |

Old direct routes (Gateway, Ledger, QA etc.) still work — they're accessible via Settings sub-tabs.

---

## Files Changed

| File | Type | Change |
|------|------|--------|
| `apps/web/src/app/mission-control/constants.ts` | Modified | MC_SUB_NAV: 11 → 5 tabs |
| `apps/web/src/app/onboarding/page.tsx` | New | 4-step wizard |
| `apps/web/src/app/onboarding-guard.tsx` | New | Client-side redirect guard |
| `apps/web/src/app/layout.tsx` | Modified | `<OnboardingGuard />` inside BrandProvider |
| `apps/web/src/app/mission-control/page.tsx` | Modified | Redesigned as Home Inbox |
| `apps/web/src/app/mission-control/content/page.tsx` | New | Content tab |
| `apps/web/src/app/mission-control/components/quick-capture.tsx` | New | Floating "+" button |
| `apps/web/src/app/mission-control/settings/page.tsx` | Modified | 4 settings sub-tabs |
| `apps/api/tests/test_slice88.py` | New | 18 tests |

---

## Key Components

### `OnboardingGuard`
- Client component placed inside `BrandProvider`
- Reads `localStorage.getItem('onboarding_done')` and `brands.length`
- If neither set, redirects to `/onboarding`
- Skips auth pages and `/onboarding` itself

### Home Inbox (`/mission-control`)
- **Approval queue**: deliverables with `status=review` + high/urgent notifications
- **Reject flow**: 4 structured tags — `Wrong voice`, `Bad hook`, `Needs research`, `Off-topic` — POSTed to `/agent-api/report` with `report_type: "voice_feedback"` → stored in agent_memory
- **7-day strip**: ✅ published / 📅 scheduled / 📝 draft / · empty
- **Agent status**: top 4 agents with live/idle indicator
- **Latest from Jumbo**: today's briefing notification

### Content Tab (`/mission-control/content`)
- **Pipeline bar**: Researching → Writing → QA → Ready (counts from deliverables + active tasks)
- **Trending topics**: from last Trend Analyzer deliverable (fallback to static examples)
- **Content queue**: filter by draft / scheduled / published; each item shows platform badge + edit link

### Quick Capture
- Fixed bottom-right `+` button on all MC pages
- Opens 3-option modal: Write a post → Composer, Save an idea → Inspo, Voice note → Telegram

### Settings Expansion
- Added `SETTINGS_TABS` constant: Connectors (inline), Playbooks (→/playbooks), History (→/ledger), System (→/gateway)
- Styled as underline tab bar, matching MC design language

---

## Security

- No new API endpoints — all reuse existing authenticated routes
- Rejection feedback uses `agentBridgeApi.submitReport` (JWT-authenticated)
- Onboarding redirect guard only runs client-side (no SSR data exposure)

---

## Testing

```
pytest apps/api/tests/test_slice88.py -v
→ 18/18 pass

npx tsc --noEmit
→ 0 errors
```

### Test Classes

| Class | Count | Covers |
|-------|-------|--------|
| `TestNavRestructure` | 3 | Exactly 5 tabs, correct labels, Home → /mission-control |
| `TestOnboarding` | 5 | Page exists, 4 steps, brand create, foundation save, guard |
| `TestHomeInbox` | 4 | Approval section, 7-day strip, agents, reject tags |
| `TestContentTab` | 3 | Pipeline stages, queue filters |
| `TestSettingsExpansion` | 3 | 4 sub-tabs, connectors default, old routes |

---

## Gaps Closed

| Gap | Status |
|-----|--------|
| New user has no onboarding | ✅ Fixed — 4-step wizard |
| 11 confusing technical tabs | ✅ Fixed — 5 user-friendly tabs |
| Approval buried 3 clicks deep | ✅ Fixed — surfaces immediately on Home |
| No content calendar overview | ✅ Fixed — 7-day strip on Home + queue on Content |
| No quick content capture | ✅ Fixed — floating "+" on all MC pages |
| Agent rejections not tracked | ✅ Fixed — structured tags → agent_memory |
