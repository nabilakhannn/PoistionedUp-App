# Slice 87: Starter Kit Export + Voice Note Input

**Date:** 2026-03-02
**Tests added:** 21 (1282 total)
**New failures:** 0
**Files changed:** 18

---

## Problem

Two gaps identified after 86 slices:

1. **Starter Kit gap**: PositionedUp's production agent system (8 SOUL.md files, HEARTBEAT.md,
   openclaw.json, memory system) existed only as live code — no sharable templates. A LinkedIn post
   prompted the question "do we have these?" and the answer was "yes, but only as a running system,
   not as distributable templates." The one real architectural gap: no `user.md` portable profile
   (user context lives in Supabase, not a file agents can read on first contact).

2. **Voice Note gap**: Jumbo already received Telegram DMs via @Jumbohere_bot. Whisper transcription
   already existed (`ingestion.py:transcribe_audio_bytes()`). But there was no handler when a user
   sent a voice note — Jumbo had no way to transcribe it and route the intent.

---

## Solution

### Part A: Starter Kit (11 new files, 1 JSON template)

Created `starter-kit/` folder with generalized, production-derived templates:

```
starter-kit/
├── README.md                      — 5-step setup guide + voice workflow
├── user.md                        — User profile template (5 sections, fill-in-once)
├── SOUL.md                        — System constitution (trust boundaries, cost guardrails, model rules)
├── HEARTBEAT.md                   — Execution protocol (6 routing rules, agent-specific priorities)
├── openclaw-template.json         — Full agent runtime config (5 agents, Telegram, 3 cron schedules)
├── architecture.md                — ASCII component diagram + 5-component explanation
└── agents/
    ├── orchestrator/SOUL.md       — Orchestrator template (reads user.md, voice notes, Brain API)
    ├── researcher/SOUL.md         — Researcher template (check knowledge base before web search)
    ├── writer/SOUL.md             — Writer template (voice-matched, hook-first, mobile-readable)
    ├── qa-reviewer/SOUL.md        — QA reviewer template (6-dimension scoring, AI-tell detection)
    └── publisher/SOUL.md          — Publisher template (hard rule: never post without approval)
```

**Key design principle:** Every template has `[CUSTOMIZE]` markers for domain-specific values
(task prefix, platforms, timezone, Brain API URL) while keeping the production-grade structural
patterns (trust boundaries, cost guardrails, heartbeat protocol) intact.

**Why `user.md` matters:** This closes the last conceptual gap — user context is now a portable
markdown file that any agent system can read on first contact, not locked in a database. The
Orchestrator template reads it on startup with `file_read("user.md")`.

### Part B: Voice Note Input Backend

**New service: `apps/api/app/services/voice_notes.py`**

Two-step Telegram download + Whisper transcription pipeline:

```
file_id → Telegram getFile API → file_path (validated) → download bytes
                                                            ↓
                                              transcribe_audio_bytes() [existing Whisper]
                                                            ↓
                                              {transcript, language, char_count, error}
```

Key security decisions:
- `bot_token` comes from `settings.telegram_bot_token` (env var) — NEVER accepted from request
- `_validate_file_path()` rejects path traversal, non-audio extensions, shell injection chars
  using a strict regex: `^[a-zA-Z0-9/_\-]+\.(?:oga|ogg|mp3|wav|m4a|flac|webm)$`
- `TELEGRAM_API_BASE = "https://api.telegram.org"` hardcoded — no SSRF via dynamic base URL
- Download errors return a safe error dict (never bubble up raw Telegram API responses)

**New endpoint: `POST /agent-api/voice/transcribe`** (added to `agent_bridge.py`)

```
X-Agent-Key: required (existing agent auth)
Body: { "file_id": "AwACAgI...", "duration_seconds": 30 }
Response: { "transcript": "...", "language": "en", "char_count": 42, "duration_seconds": 30, "error": "" }
```

Returns 200 even on transcription errors (error field set). Jumbo handles gracefully.

**Updated: `agents/jumbo/SOUL.md`**

Two new sections added:

1. **`## STARTUP BEHAVIOR — USER PROFILE`**: On first Telegram contact, Jumbo reads `user.md`.
   If found → loads profile + greets by name. If not found → guides user to create it.

2. **`## VOICE NOTE HANDLING — TELEGRAM`**: OpenClaw transcribes natively (see Activation Notes).
   The transcript arrives as a regular text message. Jumbo routes intent normally.
   NEVER post directly from voice note — always through pipeline with human approval.

**Updated: `apps/api/app/config.py`**

Added `telegram_bot_token: str = ""` to Settings (same token as openclaw.json `TELEGRAM_BOT_TOKEN`).

---

## Architecture

```
User voice note → Telegram → OpenClaw
                                  ↓
                     tools.media.audio config (openclaw.json on VPS):
                     provider=openai, model=whisper-1
                     [OpenClaw calls OpenAI Whisper API directly]
                                  ↓
                     Transcript replaces message body (plain text)
                                  ↓
                     Jumbo receives text — routes intent as normal:
                     "create/write/post" → pipeline/trigger (topic=transcript)
                     "remember/save"     → knowledge/create
                     "what/how"          → brain context answer
                     default             → pipeline/trigger

Fallback (if OpenClaw transcription fails):
Jumbo can call POST /agent-api/voice/transcribe {file_id}
→ voice_notes.py downloads from Telegram + calls Whisper
→ returns {transcript, language, char_count, error}
```

**VPS config required** (`/root/.openclaw/openclaw.json`):
```json
"tools": {
  "media": {
    "audio": {
      "enabled": true,
      "maxBytes": 20971520,
      "models": [{ "provider": "openai", "model": "whisper-1" }]
    }
  }
}
```

**Note:** OpenClaw 2026.2.26 has a MIME bug (`audio/ogg; codecs=opus` not auto-detected as audio).
Explicit `tools.media.audio` config bypasses the auto-detection path and forces Whisper.
Fix is in the unreleased 2026.3.x branch.

---

## Files Changed

| File | Type | Change |
|------|------|--------|
| `starter-kit/README.md` | NEW | 5-step setup guide |
| `starter-kit/user.md` | NEW | User profile template (5 sections) |
| `starter-kit/SOUL.md` | NEW | System constitution template |
| `starter-kit/HEARTBEAT.md` | NEW | Heartbeat execution protocol template |
| `starter-kit/openclaw-template.json` | NEW | 5-agent runtime config template |
| `starter-kit/architecture.md` | NEW | ASCII diagram + component explanations |
| `starter-kit/agents/orchestrator/SOUL.md` | NEW | Orchestrator template |
| `starter-kit/agents/researcher/SOUL.md` | NEW | Researcher template |
| `starter-kit/agents/writer/SOUL.md` | NEW | Writer template |
| `starter-kit/agents/qa-reviewer/SOUL.md` | NEW | QA reviewer template |
| `starter-kit/agents/publisher/SOUL.md` | NEW | Publisher template |
| `apps/api/app/services/voice_notes.py` | NEW | Telegram download + transcribe service |
| `apps/api/tests/test_slice87.py` | NEW | 21 tests |
| `apps/api/app/routers/agent_bridge.py` | MODIFIED | Added `POST /agent-api/voice/transcribe` |
| `apps/api/app/config.py` | MODIFIED | Added `telegram_bot_token` to Settings |
| `agents/jumbo/SOUL.md` | MODIFIED | Added user.md startup + voice note sections |
| `docs/compound/project-log.md` | MODIFIED | Slice 87 entry |
| `memory/MEMORY.md` | MODIFIED | Updated counts |

---

## Security

| Risk | Mitigation |
|------|-----------|
| Token leak via request body | `bot_token` read from `settings.telegram_bot_token` only. Endpoint rejects any `bot_token` in request body (tested). |
| SSRF via Telegram file_path | `_validate_file_path()` regex blocks traversal + non-audio extensions. `TELEGRAM_API_BASE` hardcoded to `https://api.telegram.org`. |
| Audio from other bots | `file_id` is scoped to the Telegram bot — only files uploaded to YOUR bot can be downloaded with YOUR token. |
| Large audio files | 25MB limit enforced by existing `transcribe_audio_bytes()` — returns error, not crash. |
| Direct publish from voice | Jumbo SOUL.md explicitly states: "NEVER post directly from a voice note — always go through the pipeline". |

---

## Test Coverage (21 tests)

| Class | Count | What |
|-------|-------|------|
| `TestTelegramAudioDownload` | 3 | Download success, HTTP error, missing token |
| `TestTranscribeVoice` | 3 | Whisper delegation, error pass-through, whitespace stripping |
| `TestVoiceService` | 2 | Download failure graceful return, transcription failure graceful return |
| `TestVoiceEndpointSecurity` | 4 | Token not in request body, path traversal blocked, valid paths pass, HTTPS enforced |
| `TestStarterKitFiles` | 9 | All 11 files exist, user.md has 5 sections, JSON is valid, Jumbo SOUL.md updated |

---

## Reuse

| Existing asset | Reused for |
|---------------|-----------|
| `ingestion.py:transcribe_audio_bytes()` | Whisper transcription (no new Whisper code) |
| `agent_bridge.py:get_agent_caller()` | Auth for voice endpoint |
| `config.py:Settings` | Added one field, used existing pattern |
| All 8 production SOUL.md files | Structural templates for starter kit (generalized) |
| `HEARTBEAT.md` | Starter kit heartbeat template (generalized) |
| `openclaw.json` | Starter kit config template (generalized) |

---

## Activation Notes

**To enable voice notes (DONE — already live):**
1. ✅ `TELEGRAM_BOT_TOKEN` set in Vercel backend
2. ✅ API deployed
3. ✅ `tools.media.audio` added to `/root/.openclaw/openclaw.json` on VPS:
   `{"enabled":true,"maxBytes":20971520,"models":[{"provider":"openai","model":"whisper-1"}]}`
4. ✅ Gateway restarted — `openai-whisper-api` skill registered at startup
5. Voice notes to @Jumbohere_bot → OpenClaw transcribes via Whisper → Jumbo routes intent

**To distribute the starter kit:**
- All 11 files in `starter-kit/` are ready to share as-is
- Replace `[CUSTOMIZE]` markers with your specific values
- The only thing missing is the Brain (knowledge system) — minimal Brain = a JSON endpoint

---

## Gaps Closed

- ✅ `user.md` — portable user profile template (was stored in DB only)
- ✅ Voice note input via Telegram (was text-only before)
- ✅ Starter kit templates (production system was not distributable before)
