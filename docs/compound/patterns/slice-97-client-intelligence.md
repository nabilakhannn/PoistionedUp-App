# Slice 97 + 98 — Client Intelligence System

**Date:** March 2026 | **Status:** Complete

---

## What Was Built

Three agents power the end-to-end client workflow for a content agency:

1. **Brand Researcher** — 5-layer deep research (LinkedIn/voice, anxiety list, benefit list, emotional journals, Hormozi Value Equation, competitor gap) from LinkedIn + website + intake form
2. **Account Manager** — reads call transcripts + intake form + last 3 sessions (cross-call memory), builds 7-category action plan, dispatches to all agents
3. **Client Deliverables** — HTML proposals, landing pages, nurture sequences — generated from research + transcript

---

## Database

### `client_intake_forms` (migration 037)
Public shareable form — client fills it before the discovery call.

```sql
share_token VARCHAR(64) UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex')
-- 16+ fields: industry, offer, price, target_audience, best_3_clients, etc.
```

RLS: "Users manage own" + "Public read by share_token" (USING true — allows unauthenticated reads)

### `account_manager_sessions` (migration 038)
One row per analyzed call. Tracks cross-call memory.

```sql
call_number       INTEGER DEFAULT 1
cross_call_themes JSONB DEFAULT '[]'  -- recurring topics across all calls
action_plan       JSONB DEFAULT '[]'  -- 7-category items
status            VARCHAR(30) DEFAULT 'pending_review'
```

### `agent_deliverables` (extended)
```sql
share_token  VARCHAR(64) UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex')
version      INTEGER DEFAULT 1
client_brand BOOLEAN DEFAULT false
```

### `personal_brands` (extended)
```sql
is_client_brand BOOLEAN DEFAULT false
```

---

## Profile JSON Schema (expanded for client brands)

When `is_client_brand=true`, `profile_json` contains:

```json
{
  "content_pillars": ["..."],
  "voice_adjectives": ["..."],
  "ica_summary": "...",
  "hormozi": {
    "dream_outcome": "...",
    "perceived_likelihood": "...",
    "time_to_result": "...",
    "effort_sacrifice": "...",
    "guarantee": "...",
    "risk_reversals": ["..."]
  },
  "anxiety_list": ["20 specific items"],
  "benefit_list": ["20 specific items"],
  "emotional_pain_journal": "500-word journal from ICP in the pain",
  "emotional_win_journal": "500-word journal from ICP with the result",
  "competitors": [{"name": "...", "positioning": "...", "gap": "..."}],
  "competitor_gap": "The one thing they can uniquely own",
  "first_week_angles": [
    {
      "hook": "...",
      "angle_type": "anxiety|benefit|story|competitor",
      "driven_by": "anxiety_list[0]",
      "offer_connection": "leads to free assessment"
    }
  ]
}
```

---

## Emotional Journal Injection Pattern

When `is_client_brand=true`, `fetch_brand_profile` tool injects extra context:

```python
# In tool_use_agents.py _exec_fetch_brand_profile:
if profile.get("is_client_brand"):
    result["emotional_pain_journal"] = profile_json.get("emotional_pain_journal", "")
    result["emotional_win_journal"] = profile_json.get("emotional_win_journal", "")
    result["anxiety_list"] = profile_json.get("anxiety_list", [])
    result["benefit_list"] = profile_json.get("benefit_list", [])
    # These feed: copywriter hooks, landing page hero copy, ad creative angles
```

---

## Public Routes Pattern (no auth)

Two intentionally public routes use random hex tokens for security:

```python
# intake.py
_TOKEN_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)

@router.get("/{share_token}")  # No Depends(get_current_user)
async def get_public_intake_form(share_token: str):
    if not _TOKEN_RE.match(share_token):
        raise HTTPException(400)
    # ...

# client_deliverables.py
@router.get("/share/{share_token}")  # HTMLResponse, no auth
async def share_deliverable(share_token: str):
    # Returns HTMLResponse for proposals/landing pages
    # Returns JSON wrapped in HTML for nurture sequences
```

The 64-char hex token (32 random bytes) provides 256 bits of entropy — mathematically unguessable.

---

## Cross-Call Memory Pattern

Before analyzing a new transcript, load last 3 sessions:

```python
# account_manager.py
prev = (
    admin.table("account_manager_sessions")
    .select("call_number, call_date, summary, cross_call_themes")
    .eq("brand_id", brand_id).eq("user_id", user_id)
    .order("created_at", desc=True).limit(3)
    .execute()
)
prev_sessions = prev.data or []
next_call_number = (prev_sessions[0]["call_number"] + 1) if prev_sessions else 1
# Build context: "This is call #4. Previous calls covered: ..."
# Agent can identify: "pricing came up in calls 2, 3, and now 4 — HIGH priority"
```

---

## read_agent_training_docs Tool

New tool added to `tool_use_agents.py` — always called first by Brand Researcher + Account Manager:

```python
{
    "name": "read_agent_training_docs",
    "description": "Load training materials uploaded by the user for this specific agent (PDFs, frameworks, books). Always call this first.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string"},
            "user_id": {"type": "string"}
        },
        "required": ["agent_id", "user_id"]
    }
}
# Implementation: SELECT from knowledge_documents WHERE agent_scope @> [agent_id]
# Returns formatted markdown chunks injected into agent context
```

---

## UX Flow

### 8-Step Client Onboarding Wizard (`/onboarding/client`)

```
Step 1 → Client's name → creates PersonalBrand (is_client_brand=true)
Step 2 → LinkedIn URL
Step 3 → Website (skip)
Step 4 → Main offer + price (skip)
Step 5 → Best 3 clients (skip)
Step 6 → Content goal [3 buttons] → triggers research
Step 7 → Animated research progress (60-90s)
Step 8 → Brand Intelligence Report + Guided Next Steps
```

Post-research screen shows:
- 5 content angle cards with [Write Post →] buttons
- Schedule selector (Daily / 3x/week / Weekly)
- Client intake form share link

### Account Manager Flow

```
Mission Control → 🎙 Analyze Client Call (inline panel)
→ TranscriptDrop [Paste | Upload | Intake | MCP]
→ AccountManagerPanel (7 categories)
→ [Approve All] / per-item approve
→ [Save Changes] → dispatches to agents
→ Deliverable items → [Generate] → appears in /deliverables
```

---

## Security Checklist

| OWASP | Control | Location |
|-------|---------|----------|
| A01 IDOR | `.eq("user_id", user.id)` on all queries | All routers |
| A03 Injection | `_UUID_RE.match()` on all IDs | All routers |
| A07 Auth | `Depends(get_current_user)` on private endpoints | All private routes |
| A10 SSRF | `validate_url_for_fetch()` before any HTTP | client_researcher.py, client_deliverables.py |
| A04 Upload | 10MB cap on PDF training docs | agent-training-panel.tsx |
| A05 Data | Transcript content never exposed in share links | account_manager.py |
| Public routes | 64-char random hex token (256-bit entropy) | intake.py, client_deliverables.py |
