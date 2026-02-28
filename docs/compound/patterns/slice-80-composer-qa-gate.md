# Slice 80 — Composer → QA Gate

**Date:** 2026-02-27
**Status:** Complete
**Tests:** 1159 total (8 new) | 0 TS errors

---

## What Was Built

Wired the existing QA scoring engine (Slice 76) into the Composer page. Users can now run a quality check before scheduling content, see a 6-dimension score breakdown, and get warned if they try to schedule low-quality content. Also fixed a broken AI Generate button (wrong endpoint path).

## Files Changed

| Action | File | What |
|--------|------|------|
| MODIFY | `apps/web/src/app/composer/page.tsx` | QA Check button, result panel, soft gate warnings |
| MODIFY | `apps/web/src/lib/api/composer.ts` | Fix content-chat endpoint path (`/content-chat` → `/content-chat/message`) |
| CREATE | `apps/api/tests/test_composer_qa_gate.py` | 8 new tests |

## Key Improvements

### 1. QA Check Button in Composer
New violet "QA Check" button in the action strip (before Save Draft). Calls `POST /qa/review` with the current post body, platform, and brand context. Shows a spinning loader during the API call and an inline `ScoreBadge` with the result score.

### 2. QA Result Panel
When a QA check completes, a detailed result panel appears in the right column (between Preview and Writing Tips):
- **Header:** Overall score badge + verdict pill (Pass/Revise/Fail)
- **Dimension scores:** 6-dimension grid (voice, hook, virality, ai-tells, structure, goal alignment) with color-coded values
- **Feedback:** LLM-generated improvement suggestions
- **Issues:** Categorized issues with severity indicators (red/yellow/gray dots)
- **Risk flags:** Red alert box for medical claims, legal risks, etc.
- **Dismiss button:** Clears the panel

### 3. Soft QA Gate on Schedule/Queue
When clicking "Schedule For..." or "Add to Queue":
- **No QA check run:** Confirm dialog — "You haven't run a QA check yet. Schedule anyway?"
- **QA verdict = fail (<50):** Confirm dialog — "QA score is X/100 (Fail). Schedule anyway?"
- **QA verdict = pass or revise:** No prompt, schedules immediately

This is a soft gate — warns but doesn't block. Users always have the final say.

### 4. Stale Score Auto-Clear
A `useEffect` clears `qaResult` whenever `body` changes, so users never see a stale score from a previous version of their content.

### 5. Content-Chat Endpoint Fix (Bonus)
`composerApi.generateContent` was calling `POST /content-chat` but the backend defines `POST /content-chat/message`. This meant the AI Generate button in the Composer was broken (404). Fixed the path.

## Reused Components
- `ScoreBadge` from `mission-control/qa/components/score-badge.tsx`
- `VERDICT_STYLES` and `SCORE_DIMENSIONS` constants from `@/lib/api/qa`
- `qaApi.review()` method from `@/lib/api/qa`
- `useBrand()` hook already imported in Composer
- `trackEvent()` already imported in Composer

## Security Checks

| Check | Status |
|-------|--------|
| QA review: auth required | Uses existing JWT via `apiFetch` |
| No new endpoints | Reuses existing POST /qa/review |
| No secrets in UI | Only displays score data |
| Confirm dialogs | Client-side only, no bypass risk |
| Content-text validation | Backend validates 1-50,000 chars |
