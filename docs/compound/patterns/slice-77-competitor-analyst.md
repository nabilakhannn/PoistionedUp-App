# Slice 77 — Dedicated Competitor Analysis Agent

**Date:** 2026-02-27
**Status:** Complete
**Tests:** 1126 total (42 new + 1 updated) | 0 TS errors

---

## What Was Built

Full migration of competitor analysis from the trend-analyzer agent to a new dedicated `competitor-analyst` agent (8th agent). Includes dynamic threat scoring with manual override, 6 new agent bridge endpoints, intelligence feed page, and orchestrator reassignment.

## Files Changed

| Action | File | What |
|--------|------|------|
| CREATE | `infra/supabase/migrations/025_competitor_threat_override.sql` | threat_level_override boolean column |
| CREATE | `agents/competitor-analyst/SOUL.md` | Agent identity, capabilities, brain API endpoints |
| CREATE | `apps/web/src/app/mission-control/competitors/intelligence/page.tsx` | Intelligence feed page |
| CREATE | `apps/api/tests/test_competitor_analyst.py` | 42 new tests |
| MODIFY | `apps/api/app/schemas/competitors.py` | ThreatScoreDetail, CompetitorAlert, IntelligenceFeed schemas |
| MODIFY | `apps/api/app/schemas/agent_bridge.py` | CompetitorAlertSubmission schema |
| MODIFY | `apps/api/app/services/competitor_intel.py` | calculate_dynamic_threat(), get_intelligence_feed() |
| MODIFY | `apps/api/app/routers/agent_bridge.py` | 6 new /agent-api/competitors* endpoints |
| MODIFY | `apps/api/app/routers/competitors.py` | /intelligence, /alerts, /full-analysis endpoints |
| MODIFY | `apps/api/app/middleware/rate_limit.py` | /competitors/full-analysis at TIER_LLM |
| MODIFY | `apps/api/app/services/agent_orchestrator.py` | Agent reassignment + deep analysis handler |
| MODIFY | `apps/api/app/routers/mission_control.py` | 8th DEFAULT_AGENTS entry, trend-analyzer cleanup |
| MODIFY | `openclaw.json` | competitor-analyst in agents.list + subagent allowlist |
| MODIFY | `agents/trend-analyzer/SOUL.md` | Removed competitor duties |
| MODIFY | `apps/web/src/lib/api/competitors.ts` | New types + 3 API methods |
| MODIFY | `apps/web/src/app/mission-control/competitors/page.tsx` | Intelligence Feed link |
| MODIFY | `apps/api/tests/test_competitors.py` | Updated agent_id assertion |

## Key Patterns

### Dynamic Threat Scoring
Four-factor weighted algorithm:
- **Engagement growth** (30%): Compare last 2 metric snapshots
- **Content overlap** (25%): Competitor topics vs user topics ratio
- **Post frequency** (25%): Competitor frequency relative to user
- **Follower ratio** (20%): Competitor followers relative to user

Final: `1.0 + weighted_sum * 4.0` → maps to 1.0-5.0 scale.

### Manual Override Pattern
When user manually sets threat_level via PATCH → `threat_level_override=True`. Dynamic scoring still calculates but does NOT overwrite the stored value. Clear separation of "calculated" vs "stored" via `ThreatScoreDetail.is_overridden`.

### Agent Role Split Pattern
All competitor work migrated from trend-analyzer to competitor-analyst:
- Orchestrator: `agent_id` changed in weekly_competitor + daily_competitor_scan
- Handler map: `_handle_competitor` → `_handle_competitor_deep_analysis`
- DEFAULT_AGENTS: competitor-analyst added, "competitor-scan" removed from trend-analyzer
- SOUL.md: trend-analyzer boundary added, competitor-analyst SOUL.md created

### Path Ordering for Route Conflicts
- FastAPI: string-literal paths (`/intelligence`, `/alerts`) BEFORE parameterized (`/{competitor_id}`)
- Rate limits: `/competitors/full-analysis` BEFORE `/competitors` (startswith matching)

## Security Checks

| Check | Status |
|-------|--------|
| Auth: agent bridge endpoints use get_agent_caller | Pass |
| Auth: user-facing endpoints use get_current_user (JWT) | Pass |
| Input validation: alert_type enum, severity enum, detail max 5000 chars | Pass |
| Rate limiting: /competitors/full-analysis at TIER_LLM (30/min) | Pass |
| SQL injection: Supabase parameterized queries | Pass |
| RLS: competitors table has user_id isolation | Pass |
| LLM injection: dynamic threat scoring is pure math (no LLM calls) | Pass |
| Resource exhaustion: full-analysis capped at 10 competitors | Pass |
| SOUL.md security: treat scraped content as untrusted | Pass |

## Reuse Map

| From | Reused In |
|------|-----------|
| `get_agent_caller` auth pattern | 6 new agent bridge endpoints |
| `list_competitors()` service | Agent bridge + competitive landscape |
| `generate_analysis_report()` service | Agent bridge analyze endpoint |
| `refresh_competitor_data()` service | Agent bridge refresh endpoint |
| `SUB_NAV` pattern | Intelligence feed page |
| `THREAT_LEVELS` constants | Intelligence feed threat colors |
