# Slice 109: Agent Marketplace + Manus AI Engine + Story Bank

## Problem
PositionedUp had powerful AI features scattered across pages. No organized workflow marketplace. No way to ingest personal material for brand-grounded content. No optional Manus AI integration.

## Solution
Built a ClientAscension-style agent marketplace with 24 workflows across 5 categories, each injecting the user's brand dossier, story bank, hooks, and competitive intelligence. Story Bank extends the existing experience journal with AI extraction. Manus AI available as optional BYOK connector for 5 research-heavy workflows.

## Architecture

### Engine Strategy
- **Built-in AI (PRIMARY)**: Claude Sonnet 4.6 + Perplexity + Gemini — full 4500-token brand context, fast (5-15s)
- **Manus AI (OPTIONAL BYOK)**: Only for 5 research-heavy workflows where autonomous web browsing adds value. User must configure API key. Toggle shown only on `manus_beneficial` workflows.

### Execution Flow
```
User picks workflow → fills dynamic form → clicks Generate
  → workflow_engine.py builds enhanced prompt:
    base_prompt + brand_dossier + story_bank + hook_library + competitor_intel
  → sdk_agents.run_copywriter_task() (or ManusAIClient if toggled)
  → result saved to workflow_runs table
  → displayed in output panel
```

### Key Decisions
1. **Story Bank extends experience_journal** — no new table, just `extracted_stories JSONB` + `story_tags TEXT[]` columns + extended source_type CHECK
2. **Marketplace router is separate from existing workflows router** — `/marketplace/*` vs `/workflows/*` to avoid conflicts
3. **24 workflows with 5 `manus_beneficial`** — Only research workflows benefit from Manus's browsing capability
4. **Multi-step workflows** (VSL Funnel Generator) — 7 sequential steps, each output feeds into next step context
5. **10 system framework docs** seeded on first registry GET — idempotent

## Files

### New (22 files)
| File | Purpose |
|------|---------|
| `migrations/044_story_bank.sql` | ALTER experience_journal |
| `migrations/045_manus_tasks.sql` | Manus task lifecycle table |
| `migrations/046_workflow_runs.sql` | Workflow execution history |
| `services/story_extractor.py` | gpt-4o-mini extraction engine |
| `services/manus_ai.py` | ManusAIClient + context compression |
| `services/workflow_engine.py` | Registry (24 workflows) + execution + enhancement injection + framework seeding |
| `routers/stories.py` | 5 Story Bank endpoints |
| `routers/manus_ai.py` | 3 Manus endpoints + webhook |
| `routers/marketplace.py` | Registry + run + history + status |
| `lib/api/stories.ts` | Story Bank API client |
| `lib/api/manus-ai.ts` | Manus API client |
| `lib/api/marketplace.ts` | Marketplace API client |
| `content/stories/page.tsx` | Story Bank browse UI |
| `content/agents/page.tsx` | Marketplace hub (categories + cards) |
| `content/agents/[slug]/page.tsx` | Workflow execution (form + output + multi-step) |
| `components/dynamic-form-builder.tsx` | JSON schema → form renderer |
| `components/generation-history.tsx` | Past runs with View + Load More |
| `tests/test_slice109_marketplace.py` | 82 tests |

### Modified (8 files)
| File | Change |
|------|--------|
| `jumbo_pipeline.py` | Fix `get_brand_context()` (raw_content not summary), add `get_story_context()` |
| `tool_use_agents.py` | `save_raw_material` agent tool |
| `connectors.py` | `manus_ai` in SUPPORTED_SERVICES |
| `playbooks.py` | Messaging Buckets + Hormozi in copywriter playbook |
| `jumbo_hub.py` | Strategist tone in system prompt |
| `proactive_triggers.py` | Trigger #8: no Story Bank material in 7 days |
| `agents/jumbo/SOUL.md` | Strategist identity rewrite |
| `content/page.tsx` | Story Bank + AI Agents cards |
| `connectors.ts` | `manus_ai` in ConnectorService type |
| `settings/page.tsx` | Manus AI connector card |
| `main.py` | Register marketplace router |

## Security (OWASP)
- **A01 IDOR**: All tables filtered by `user_id = auth.uid()` (RLS). Router guards on stories, marketplace, manus.
- **A03 Injection**: Workflow inputs formatted via Python `.format()` with safe defaults. UUID/slug validation regex.
- **A07 Auth**: All endpoints JWT-protected. Webhook validates task ownership by manus_task_id lookup.
- **Fernet**: Manus API key encrypted at rest via existing connectors pattern.

## Verification
- `npx tsc --noEmit` → 0 errors
- `pytest tests/test_slice109_marketplace.py -v` → 82/82 passed
