# Slice 91b — Zero-Setup Onboarding
## LinkedIn URL → 30 Seconds → Brand Profile Built from Your Real Content

**Date:** March 2026
**Status:** Completed
**Tests:** 15 new (1368 total, +15 from 1353)
**TS Errors:** 0

---

## Problem

Users arriving after onboarding (Slice 88) had empty `profile_json` because most skipped the
"paste 3 posts" step. Agents then produced generic output on their first run — no voice, no ICA,
no positioning to work from.

**The fix:** Give your name + any public URL → Perplexity finds your public content → Claude
extracts voice, ICA, positioning, offer → profile fills in 30 seconds, automatically.

---

## What Was Built

### 1. Backend — `POST /brands/{brand_id}/auto-profile`

**File:** `apps/api/app/routers/brands.py`

Three steps (single endpoint call, ~30s):

```
1. Research:   Perplexity web search → Tavily fallback → or just use extra_context
2. Synthesis:  Claude Sonnet 4.6 extracts foundation/ica/offer/positioning/summary JSON
3. Save:       Deep-merge into profile_json — ONLY fills empty fields, never overwrites
```

**Request model:**
```python
class AutoProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    public_url: str = ""       # LinkedIn, website, X/Twitter
    extra_context: str = ""    # Optional extra context from user
```

**Response:**
```json
{ "ok": true, "sections_filled": ["foundation", "ica"], "summary": "...", "data_found": true }
```

**Security:**
- `public_url` → `validate_url()` from `app/utils/url_validation.py` (SSRF protection)
- `full_name` → `_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9 '\-\.\,]")` strips injection chars
- URL is never fetched directly — only used as Perplexity search context hint
- Brand ownership verified via `_verify_brand_ownership()` (IDOR protection)

**Graceful degradation chain:**
```
Perplexity key present → search
    └─ no results → Tavily fallback
        └─ no results → if extra_context → save to foundation.beliefs
            └─ returns data_found: false (never hard errors)
```

**Key functions added:**
- `_search_perplexity(query, api_key) -> str` — returns snippets or "" on any failure
- `_search_tavily(query, api_key) -> str` — Tavily fallback
- `_synthesize_profile(research_text, full_name, extra_context) -> Optional[Dict]`
- `_save_profile_sections(admin, brand_id, user_id, profile) -> List[str]`
- `_SAFE_NAME_RE` — name sanitization regex
- `_AUTO_PROFILE_SYSTEM` — system prompt for Claude extraction

---

### 2. TypeScript Client — `apps/web/src/lib/api/brand.ts`

Added to `personalBrandsApi`:
```typescript
autoProfile: (brandId: string, data: {
  full_name: string; public_url?: string; extra_context?: string;
}) => apiFetch<{ ok: boolean; sections_filled: string[]; summary: string; data_found: boolean }>(
  `/brands/${brandId}/auto-profile`,
  { method: "POST", body: JSON.stringify(data) },
)
```

---

### 3. Onboarding Step 2 — `apps/web/src/app/onboarding/page.tsx`

Step 2 redesigned from "paste 3 posts" to a two-tab UI:

```
┌──────────────────────────┬──────────────────────────┐
│  🤖 AI Auto-Fill (Rec.) │  ✍️ Paste Posts Manually  │
│                          │                           │
│  Name: [______________]  │  Post 1: [_____________] │
│  Public URL: [_________] │  Post 2: [_____________] │
│  Context: [___________]  │  Post 3: [_____________] │
│                          │                           │
│  [Analyze in 30s →]      │  [Continue →]             │
└──────────────────────────┴──────────────────────────┘
```

**AI tab flow:**
1. Name + optional URL → "Analyze in 30s →" button
2. Loading: "Analyzing your content…"
3. Success: preview card with extracted summary + sections filled count + "Looks right → Continue"
4. Failure / no data: friendly message + falls through to manual tab option
5. "Edit manually instead" link for escape hatch

**State added:** `step2Tab`, `aiName`, `aiUrl`, `aiContext`, `analyzing`, `aiResult`

---

### 4. Settings — `apps/web/src/app/mission-control/settings/page.tsx`

Added "Rebuild Profile from Web" card in Team & System tab:
- Name field + Public URL field + optional context
- "Rebuild Profile →" button calls `autoProfile()`
- Shows success (sections filled) or error inline
- Uses `data-testid="rebuild-profile"` for test targeting

**State added:** `rebuildName`, `rebuildUrl`, `rebuilding`, `rebuildMsg`

---

### 5. Tests — `apps/api/tests/test_slice91b_zero_setup.py`

15 tests across 5 classes:

| Class | Count | What it checks |
|-------|-------|----------------|
| `TestAutoProfileEndpoint` | 4 | Endpoint exists, ownership verification, request model, response keys |
| `TestAutoProfileSecurity` | 3 | URL validation called, name sanitization present, graceful no-key fallback |
| `TestAutoProfileIntegration` | 4 | `_synthesize_profile` returns dict/None, key structure, `_save_profile_sections` returns list, regex strips injection |
| `TestOnboardingStep2` | 2 | Step 2 exists, AI Auto-Fill tab present |
| `TestBrandSettingsRebuild` | 2 | Settings has rebuild section, brand.ts has autoProfile method |

---

## Why LinkedIn Isn't Scraped Directly

LinkedIn actively blocks direct scraping. Passing the URL as Perplexity search context
(e.g. `site:linkedin.com/in/username`) is far more reliable and avoids:
- SSRF risk (URL never fetched by our server)
- Anti-scraping blocks (Perplexity handles indexing)
- Rate limiting

---

## Verification Checklist

- [x] `npx tsc --noEmit` → 0 errors
- [x] `pytest tests/test_slice91b_zero_setup.py` → 15/15 pass
- [x] Full `pytest tests/` → 1368 passed (27 pre-existing test_resources.py failures)
- [x] Onboarding Step 2: two tabs visible, AI tab has name + URL input
- [x] Settings Team tab: "Rebuild Profile from Web" card visible
- [x] No existing profile data overwritten (deep merge fills empty only)
- [x] Without any search key: saves extra_context, returns `data_found: false`
