# Slice 100 — Jumbo Brand Chat (Brand-Context-Aware AI)

**Date:** March 2026
**Tests:** 11/11 passing
**TypeScript:** 0 errors
**Status:** COMPLETE

---

## What Was Built

A brand-context-aware chat panel embedded in the Brand Intelligence Report.
The agency owner can type custom requests or click 6 quick action buttons.
Jumbo responds with personalized materials generated directly from the client's
full 8-section Brand Intelligence Dossier — no copy-pasting, no context switching.

**Quick Actions:**
| Button | What Jumbo Generates |
|--------|---------------------|
| 📎 30 Hooks | 30 hooks organized by type (anxiety/benefit/story/competitor/belief/metaphor), 5 per type |
| 📧 Nurture Sequence | 5-email cold lead nurture with subject + body + CTA, arc: Pain→Empathy→Insight→Proof→Offer |
| 💎 Offer Outline | Grand Slam Offer using Hormozi framework: UVPs + dream outcome + guarantee + pricing stack |
| 💬 5 LinkedIn Posts | One per angle type, platform-native format, exact voice adjectives used |
| 🗣 Comment Drafts | 5 authority-positioning comments, no promotion, uses belief framework + niche vocab |
| 📅 90-Day Calendar | 3 posts/week × 13 weeks, themes: Month 1=Awareness, Month 2=Authority, Month 3=Conversion |

---

## Files Changed

| File | Change |
|------|--------|
| `apps/api/app/services/brand_chat.py` | NEW — Jumbo Brand Chat service with dossier injection |
| `apps/api/app/routers/brand_chat.py` | NEW — POST /brand-chat/{brand_id} with UUID + IDOR guards |
| `apps/api/app/main.py` | Added `brand_chat` import + `app.include_router(brand_chat.router)` |
| `apps/web/src/lib/api/brand-chat.ts` | NEW — API client + `QUICK_ACTIONS` array with prompts |
| `apps/web/src/components/jumbo-brand-chat.tsx` | NEW — Chat UI with quick actions, message history, copy button |
| `apps/web/src/components/brand-intelligence-report.tsx` | Added JumboBrandChat panel above Next Steps section |
| `apps/api/tests/test_slice100_brand_chat.py` | 11 tests across 3 classes |

---

## Key Architectural Decision: System Prompt Injection

**Problem:** The brand dossier (8 sections, 15+ fields) is built but not activated.

**Option A — Tool call:** Jumbo calls `fetch_brand_profile` tool during the conversation.
- Adds 1 full tool-use round trip (~8-12s extra latency)
- Risk of hitting Vercel's 60s serverless limit on complex requests

**Option B (CHOSEN) — System prompt injection:**
- Load `profile_json` from DB at request time
- Inject as JSON into `_JUMBO_CHAT_SYSTEM` template before calling `run_tool_use_agent()`
- Jumbo sees full dossier from message 1 — no tool call needed
- Removes ~10s latency, keeps responses well under 60s

```python
# brand_chat.py — key pattern
system_prompt = _JUMBO_CHAT_SYSTEM.format(dossier_json=dossier_json)
result = run_tool_use_agent(
    agent_id="jumbo",
    task_type="brand_chat",
    system_prompt=system_prompt,   # ← dossier pre-loaded
    user_prompt=user_prompt,
    available_tools=["web_search", "read_agent_training_docs"],
)
```

---

## Token Management: `_trim_dossier()`

The full 8-section dossier can be 6-10k tokens (emotional journals are 500+ words each).
`_trim_dossier()` caps it for the system prompt:

```python
def _trim_dossier(profile):
    # Cap long lists to 10 items
    for key in ("anxiety_list", "benefit_list", "first_week_angles", ...):
        profile[key] = profile[key][:10]
    # Truncate journals to 800 chars
    for key in ("emotional_pain_journal", "emotional_win_journal"):
        profile[key] = val[:800] + "..."
    # Cap competitors to 3, false_beliefs to 3, customer_segments to 3
```

---

## Security Check (OWASP)

- **A01 IDOR:** `.eq("user_id", user_id)` on `personal_brands` lookup in service
- **A03 Injection:** `_UUID_RE.match(brand_id)` in router before any DB access
- **A07 Auth:** `Depends(get_current_user)` on POST endpoint
- **A10 SSRF:** Not applicable — no user-supplied URLs in this feature
- **Message length cap:** `max_length=5000` in Pydantic `ChatRequest` model

---

## UI Pattern — Chat Panel in Brand Intelligence Report

The chat panel is inserted between "Content Angles" and "Next Steps":

```
📊 Brand Intelligence Report
├── [grid] Content Pillars, Voice DNA, ICA Summary...
├── [grid] Transformation, UVPs, Metaphors, Your Story...
├── [full-width] Content Angles (All Types)
├── [full-width] ⚡ Ask Jumbo  ← NEW (Slice 100)
│   ├── Quick action chips (📎 📧 💎 💬 🗣 📅)
│   ├── Chat history (user bubbles + Jumbo responses)
│   └── Input box + Send button
└── [full-width] Next Steps (intake link, launch)
```

---

## Gap Analysis for Slice 101

- **GAP B: Offer Creator Agent** — reads complete 8-section dossier → generates structured Grand Slam Offer document (persistent, shareable, editable)
- **GAP C: Hook Library** — Jumbo Brand Chat can generate hooks on demand (partially closed), but a persistent Hook Library with 30+ hooks saved to DB and categorized by type would close it fully
- **GAP D: Client Deliverables Dashboard** — Download button for all generated materials (already started in `client_deliverables.py`)
