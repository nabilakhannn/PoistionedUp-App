# Slice 76: QA Agent — Content Quality Assurance

**Date:** 2026-02-27
**Status:** COMPLETED
**Tests:** 1084 total (49 new), 0 TypeScript errors

## What Was Built

A dedicated QA Agent system that reviews all content before publishing, scoring it across 6 dimensions with a two-phase engine (rule-based + LLM).

### Core System

1. **Two-Phase Scoring Engine** (`app/services/qa_review.py`)
   - Phase 1: Rule-based checks (forbidden words, em dashes, semicolons, reversal patterns, AI-tell patterns, platform length limits)
   - Phase 2: LLM scoring (voice alignment, hook strength, structure, virality potential, goal alignment)
   - Phase 3: Weighted aggregation (Voice 25%, Hook 20%, Virality 20%, AI-Tell 15%, Structure 10%, Goal 10%)
   - Conservative minimum: for dimensions with both rule and LLM scores, takes the MIN

2. **Scoring Dimensions** (0-100 each)
   - Voice Score — brand voice alignment
   - Hook Score — opening hook strength
   - Structure Score — completeness & formatting
   - AI-Tell Score — AI-tell cleanliness (inverted: 100 = no AI tells)
   - Virality Score — virality potential based on top-performing patterns
   - Goal Alignment Score — alignment with brand goals/pillars

3. **Verdict Thresholds** (strict mode)
   - Pass: score >= 80
   - Revise: score 50-79
   - Fail: score < 50

4. **Auto-Revision Pipeline**
   - When content scores < 80, creates a task for the Copywriter agent
   - Max 2 revision cycles per content piece
   - Task includes specific feedback, issues, and dimension scores

### Infrastructure

5. **Database** (`024_qa_reviews.sql`)
   - `qa_reviews` table with 6 dimension scores, verdict, feedback, issues (JSONB), risk_flags (JSONB)
   - Revision tracking (revision_number, previous_review_id)
   - RLS: `auth.uid() = user_id`
   - 3 indexes: (user_id, created_at DESC), (content_ref_type, content_ref_id), (user_id, verdict)

6. **Schemas** (`app/schemas/qa_review.py`)
   - 8 Pydantic models: QAReviewRequest, QAIssue, QARiskFlag, QAScoreBreakdown, QAReviewResult, QAStats, QAReviewOut
   - Field validators for platform, content_ref_type, severity, category

7. **Router** (`app/routers/qa.py`)
   - POST /qa/review — Score content (TIER_LLM rate limit)
   - GET /qa/reviews — List reviews with filters (TIER_READ)
   - GET /qa/reviews/{id} — Full review detail (TIER_READ)
   - GET /qa/stats — Dashboard statistics (TIER_READ)

8. **Agent Bridge** (`app/routers/agent_bridge.py`)
   - POST /agent-api/qa/review — agents can submit content for QA scoring

### Agent System

9. **QA Reviewer Agent** (`agents/qa-reviewer/SOUL.md`)
   - 7th OpenClaw agent (model: gpt-4o-mini)
   - Tools: read, write, edit, web_fetch
   - Added to openclaw.json agents.list + subagent allowlist

10. **Orchestrator Integration** (`app/services/agent_orchestrator.py`)
    - `daily_qa_review` schedule at 10am EST (cooldown: 20h)
    - `_handle_qa_review_pending()` — reviews all draft scheduled_items without QA
    - Added to DEFAULT_AGENTS in mission_control.py

11. **OpenClaw Cron** (`openclaw.json`)
    - "Daily QA Review" cron at 0 10 * * * assigned to qa-reviewer

### Frontend

12. **QA Dashboard** (`/mission-control/qa/page.tsx`)
    - Stats row: Total Reviews, Pass Rate, Avg Score, Needs Revision
    - Average dimension scores (voice, hook, virality)
    - Common issues section
    - Verdict filter (All/Pass/Revise/Fail)
    - Reviews table with click-to-expand detail

13. **Components**
    - ScoreBadge (`qa/components/score-badge.tsx`) — green/yellow/red badge
    - ReviewDetail (`qa/components/review-detail.tsx`) — 6 progress bars, issues, risk flags

14. **API Client** (`lib/api/qa.ts`)
    - Types + constants + qaApi object (review, list, get, stats)

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `infra/supabase/migrations/024_qa_reviews.sql` | Created | qa_reviews table + RLS + indexes |
| `apps/api/app/schemas/qa_review.py` | Created | 8 Pydantic models |
| `apps/api/app/services/qa_review.py` | Created | Two-phase scoring engine |
| `apps/api/app/routers/qa.py` | Created | 4 API endpoints |
| `agents/qa-reviewer/SOUL.md` | Created | Agent identity & boundaries |
| `apps/web/src/lib/api/qa.ts` | Created | TypeScript API client |
| `apps/web/src/app/mission-control/qa/page.tsx` | Created | QA Dashboard |
| `apps/web/src/app/mission-control/qa/components/score-badge.tsx` | Created | Reusable score badge |
| `apps/web/src/app/mission-control/qa/components/review-detail.tsx` | Created | Full review breakdown |
| `apps/api/tests/test_qa_review.py` | Created | 49 tests |
| `apps/api/app/main.py` | Modified | Register qa router |
| `apps/api/app/middleware/rate_limit.py` | Modified | Rate limits for /qa endpoints |
| `apps/api/app/services/agent_orchestrator.py` | Modified | Daily QA schedule + handler |
| `apps/api/app/routers/mission_control.py` | Modified | Add qa-reviewer to DEFAULT_AGENTS |
| `apps/api/app/routers/agent_bridge.py` | Modified | Add /agent-api/qa/review |
| `openclaw.json` | Modified | Add qa-reviewer agent + cron |
| `apps/web/src/app/mission-control/page.tsx` | Modified | Add QA to sub-nav |
| `apps/web/src/app/mission-control/competitors/page.tsx` | Modified | Add QA to sub-nav |
| `apps/api/tests/test_orchestrator.py` | Modified | Add qa_review_pending to handler set |
| `apps/api/tests/test_proactive_pulse.py` | Modified | Update schedule count + IDs |

## Reuse Map

| Need | Source |
|------|--------|
| Forbidden words | `worker/graph/prompts/writing_style.FORBIDDEN_WORDS` |
| Hard bans | `worker/graph/prompts/writing_style.HARD_BANS` |
| AI-tells checklist | `worker/graph/prompts/writing_style.AI_TELLS_CHECKLIST` |
| Voice DNA | `app/services/self_voice.get_voice_baseline()` |
| Performance patterns | `app/services/performance_analytics.get_performance_context()` |
| LLM client | `worker/graph/llm.get_llm_client()` |
| JSON parsing | `worker/graph/llm.parse_json_response()` |
| Model selection | `worker/graph/llm.get_model_for_step("testing")` |

## Security

- Content text length-limited (max 50,000 chars in validator)
- Content truncated to 10,000 chars for LLM calls
- Supabase parameterized queries (no SQL injection)
- RLS enforces user isolation
- Rate limiting: /qa/review at TIER_LLM
- Agent bridge uses timing-safe key comparison
- LLM prompt injection: content in USER prompt only, system prompt hardcoded

## Patterns

- **Rate limit ordering:** More specific paths (`/qa/reviews`) must come before less specific (`/qa/review`) in `_ROUTE_TIERS` because matching uses `startswith`
- **Router prefix stacking:** FastAPI `APIRouter(prefix="/qa")` means decorators use `/review` not `/qa/review`
- **Conservative scoring:** When both rule-based and LLM score a dimension, take the minimum
- **Lazy imports:** Services imported inside endpoint functions to avoid circular deps
- **Auto-revision as task:** Creates agent_tasks row, not direct API call, so it goes through normal orchestration
