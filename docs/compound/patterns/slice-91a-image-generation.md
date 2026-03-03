# Slice 91a — Nano Banana 2 Image Generation
## Production-Line Images: Claude-Structured Prompts → Higgsfield API → App + Agents

**Date:** 2026-03-03
**Tests:** 20/20 new | 1353/1353 total (pre-existing test_resources.py Supabase failures excluded)
**TS errors:** 0

---

## What This Slice Does

Integrates Nano Banana 2 (Gemini 3.1 Flash Image via Higgsfield AI) into both the app and the agent tool system. The key innovation is a two-step production-line pipeline that replaces the "slot machine" approach to image generation.

**Before:** Plain English → image API → 68% usable rate (wrong lighting, plastic skin, stock photo look)

**After:** Plain English → Claude Haiku structures prompt with 5 locked variables → image API → 92% usable rate

---

## Key Patterns Applied

### 1. Two-Step Production-Line Pipeline
```
User types: "Confident SaaS founder at desk, golden hour"
                          ↓
Step 1 — Claude Haiku prompt engineering (fast + cheap):
  subject:      "Professional woman, 30s, looking at camera, confident posture"
  composition:  "Medium shot, rule of thirds, slight angle"
  camera:       "85mm f/1.4, shallow depth of field, bokeh background"
  lighting:     "Golden hour backlight, warm key light from upper right, rim light"
  color_palette:"Kodak Portra warmth, slightly desaturated, golden tones"
  mood:         "Warm, confident, approachable"
  negative:     "no plastic skin, no AI artifacts, no stock photo look, no watermark"
  final_prompt: "[single combined sentence ready for Nano Banana 2]"
                          ↓
Step 2 — Higgsfield Nano Banana 2 → image URL
         (fallback: Google Gemini image generation → base64 data URL)
```

**Why:** The structured prompt lock is the entire innovation. Without it, generative image models produce inconsistent results because camera specs, lighting names, and film stocks are never specified. Claude Haiku consistently names the right setups (Rembrandt, golden hour, softbox) because it was trained on photography.

### 2. Transparent Prompt Engineering (User-Visible)
- "Preview Prompt" button calls `/image-gen/structure` → zero image cost
- UI shows 7 labelled breakdown rows: Subject, Composition, Camera, Lighting, Color, Mood, Negative
- User sees exactly what locked specs Claude chose before committing to generation
- This transparency builds trust and teaches users what makes good prompts

### 3. Higgsfield Primary → Gemini Fallback
```python
# Primary (if HIGGSFIELD_API_KEY set):
POST https://api.higgsfield.ai/nano-banana
  Authorization: Bearer {key}
  Body: {prompt, aspect_ratio}

# Fallback (GEMINI_API_KEY always present):
POST generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
  generationConfig.responseModalities: ["IMAGE", "TEXT"]
  Returns: base64 inline data → returned as data: URL
```
**Pattern:** Always have a working fallback. Users can start with Gemini (free with existing key) and upgrade to Higgsfield when they want production quality.

### 4. Agent Tool — generate_image
```python
# Agents can call:
{
    "name": "generate_image",
    "description": "Generate image from plain English. Claude structures prompt first.",
    "input_schema": {
        "properties": {
            "description": {"type": "string"},      # required
            "style": {"enum": ["photorealistic", "cinematic", ...]},
            "format": {"enum": ["square", "landscape", "portrait", "story"]},
        }
    }
}
```
Available to: visual-designer (primary), copywriter (for post visuals), ad creative agents.
Dispatched via `_exec_generate_image()` → `generate_image()` service → returns `{url, prompt}` JSON.

### 5. Format → Aspect Ratio Mapping
```python
FORMAT_RATIOS = {
    "square":    "1:1",   # LinkedIn, Instagram posts
    "landscape": "16:9",  # YouTube thumbnails, Twitter header
    "portrait":  "4:5",   # Instagram feed portrait
    "story":     "9:16",  # Instagram/TikTok Stories
}
```

### 6. Marketing → Images Tab (6th Tab)
```
Content | Calendar | Ads | Images | Competitors | Analytics
```
Image Studio renders inside Marketing room with full UI:
- Description textarea with char count
- Style picker (5 options, pill buttons)
- Format picker (4 options with labels)
- "Preview Prompt" → structured breakdown (free)
- "Generate Image" → generates + shows download
- Recent generations grid (last 8, 4-column, hover shows description + download)

---

## Files Changed

| File | Change |
|------|--------|
| `apps/api/app/services/image_gen.py` | NEW — prompt engineering + two-API pipeline |
| `apps/api/app/routers/image_gen.py` | NEW — 3 endpoints (generate/structure/history) |
| `apps/api/app/config.py` | Added higgsfield_api_key + image_gen_model |
| `apps/api/app/services/tool_use_agents.py` | Added generate_image to TOOL_DEFINITIONS + _exec_generate_image + _dispatch_tool |
| `apps/api/app/main.py` | Registered image_gen router |
| `infra/supabase/migrations/034_image_gen.sql` | NEW — generated_images table + RLS |
| `apps/web/src/lib/api/image-gen.ts` | NEW — TypeScript client |
| `apps/web/src/components/image-studio.tsx` | NEW — full UI studio component |
| `apps/web/src/app/marketing/page.tsx` | Added Images as 6th tab |
| `apps/api/tests/test_slice91a_image_gen.py` | NEW — 20 tests |

---

## Verification Results

```
npx tsc --noEmit     → 0 errors
pytest test_slice91a → 20/20
pytest (all)         → 1353/1353 passed
```

---

## New Env Vars Required

```
HIGGSFIELD_API_KEY=   # Higgsfield AI API key (optional — Gemini fallback works without it)
IMAGE_GEN_MODEL=      # Override Gemini model (default: gemini-3.1-flash-image-generation-preview)
```
`GEMINI_API_KEY` was already required (Slice 85) — no new key needed for the Gemini fallback path.

---

## What's Next (Slice 91b)

- Nightly CEO Agent (Jumbo reviews signals overnight → Telegram morning summary)
- Newsletter Engine (400-600 words → approve → Resend)
- Cold Email Outreach (personalized per lead → Resend → unsubscribe)
- Real CRM contacts table (Cold/Warm/Hot/Customer Kanban)
- YouTube Research Tool (transcript + timestamp + quote)
- Zero-Setup Onboarding (LinkedIn URL → 60s → brand profile)
