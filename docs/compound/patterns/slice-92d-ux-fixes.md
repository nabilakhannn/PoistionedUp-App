# Slice 92d — UX Fixes: Notion Sidebar + Kanban Error Visibility

**Date:** March 2026
**Status:** Completed
**Tests:** 8 new (1386 total, +8 from 1378)
**TS Errors:** 0

---

## Problem

Two concrete UX failures reported after Slice 92c:

1. **"Where is the competitors tab?"** — Marketing page used a horizontal 6-tab flex bar. On any viewport narrower than ~1100px, the last 1–2 tabs were cut off. Competitors (tab 5) was invisible.
2. **"Buttons are not working"** — ContentKanban silently swallowed all API errors (`catch { // ignore }`). When Add Stage / Rename / Toggle fails, the UI reverts with zero feedback — user assumes the button did nothing.

---

## What Was Built

### 1. `apps/web/src/app/marketing/page.tsx` — Notion Sidebar Layout

Replaced horizontal tab bar with a two-column `<aside> + <main>` layout.

**Before:**
```tsx
<div className="flex items-center gap-1 mt-4 -mb-px">
  {TABS.map(tab => (
    <button className="px-4 py-2 border-b-2 ...">
```

**After:**
```tsx
<div className="flex min-h-screen bg-background">
  <aside className="w-52 flex-shrink-0 border-r border-border bg-card/30">
    {/* Section list — always fully visible */}
  </aside>
  <main className="flex-1 overflow-auto">
    {/* Active section content */}
  </main>
</div>
```

**Features:**
- `<aside>` 208px wide, full-height, never overflows
- All 6 sections listed vertically: Content / Calendar / Ads / Images / Competitors / Analytics
- Active section: `bg-primary/10 text-primary` highlight
- `NoBrand` helper component reused across all 5 brand-scoped sections
- Brand name shown below room title in sidebar

### 2. `apps/web/src/components/content-kanban.tsx` — Visible Error States

Replaced all `catch { // ignore }` with visible error banners and state recovery.

**Two error states added:**

| State | Trigger | UI |
|-------|---------|-----|
| `loadError` | `stagesApi.list()` fails | Full-width red banner with Retry button |
| `actionError` | Rename / Delete / Toggle / Add fails | Amber banner at top of kanban, dismissible with ✕ |

**Recovery strategy:**
- Delete / Toggle: optimistic update → revert with `loadStages()` on failure
- Rename: revert with `loadStages()` on failure (StageColumn already reverts draft)
- Add Stage: no optimistic update — only updates on success

---

## OWASP Security Check

| Check | Status |
|-------|--------|
| A01 IDOR | ✅ No new endpoints — error states are client-only |
| A03 Injection | ✅ Error messages are hardcoded strings, no user input reflected |
| A05 Misconfiguration | ✅ Graceful fallback for every error path |
| XSS | ✅ Error strings are static literals, no `dangerouslySetInnerHTML` |

---

## SOLID Principles

| Principle | Applied |
|-----------|---------|
| S | `NoBrand` extracted as a single-purpose helper |
| O | Marketing page sections are open for extension (add to `SECTIONS[]`) |
| I | Each section receives only `brandId` prop |
| D | Components depend on API abstractions, not fetch directly |

---

## Files Changed

| File | Change |
|------|--------|
| `apps/web/src/app/marketing/page.tsx` | Horizontal tabs → Notion left sidebar |
| `apps/web/src/components/content-kanban.tsx` | Silent errors → visible banners + Retry |
| `apps/api/tests/test_slice92d_ux_fixes.py` | 8 new tests |

**No backend changes. No migrations.**

---

## Verification Checklist

- [x] `npx tsc --noEmit` → 0 errors
- [x] `pytest tests/test_slice92d_ux_fixes.py` → 8/8 pass
- [x] Full `pytest tests/` → 1386 passed (27 pre-existing test_resources.py failures)
- [x] Marketing page: left sidebar visible, all 6 sections accessible
- [x] Competitors section no longer cut off
- [x] ContentKanban: add/rename/delete failures show amber error banner
- [x] Retry button on load error works

## App URL & Manual Test Guide
**URL:** `https://web-tau-dun-23.vercel.app/marketing`

1. Open Marketing — left sidebar shows 6 sections (Content / Calendar / Ads / Images / Competitors / Analytics)
2. Click **Competitors** in sidebar → Competitor intel embed loads (or empty state)
3. Click **Calendar** → Month grid loads with ← → navigation working
4. Click **Content** → Kanban columns load. Click **+ Add Stage** → type a name → **Add**. Should create the column (or show amber error banner if API fails — never silent)
5. Click a stage name → inline rename → press Enter. Should update (or show error)
6. Click **🤖 Auto** badge → should toggle to **👤 Manual** (or show error)
