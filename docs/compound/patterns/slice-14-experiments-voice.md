# Slice 14: Experimentation + Self-Voice DNA + Drift Detection

## Pattern: A/B Testing + Voice Preservation

### Problem
The agent generates content based on observations and memories, but never deliberately
tests hypotheses. Is it actually true that story hooks outperform question hooks for
THIS creator? Without controlled experiments, we rely on gut feelings.

Also, as AI generates more content, the voice can drift from the creator's natural style.
There's no way to detect or prevent this.

### Solution: Experiments + Self-Voice DNA + Drift Detection

1. **Experiments**: Propose A/B tests (e.g., "story vs question hooks"), user approves,
   posts get assigned to variants, when enough data arrives, winner is determined.
   Winning insight becomes an agent memory (lesson).

2. **Self-Voice DNA**: Extract the creator's natural writing style from their OWN
   published posts (not reference creators). Stored in `profiles.self_voice_dna`.

3. **Drift Detection**: Compare AI-generated content against the creator's voice baseline.
   Returns a drift_score (0-1) with specific observations and recommendations.

### Architecture: Experiment Lifecycle

```
proposed → approved → running → completed
    ↓                    ↓
  cancelled          cancelled

- proposed: Agent or user suggests experiment
- approved: User approves, ready for posts
- running: Posts being assigned to variants
- completed: Winner determined, memory created
```

### Key Decision: Winner Determination

```python
WINNER_THRESHOLD = 0.30  # 30% difference needed to declare winner

if diff < WINNER_THRESHOLD:
    winner = "inconclusive"
elif a_avg > b_avg:
    winner = "variant_a"
else:
    winner = "variant_b"
```

Experiments auto-create an `agent_memory` lesson (status=pending_approval) when
a clear winner is found. The user still approves the insight.

### Pattern: Pipeline Context Injection (4th Layer)

System prompts now stack 4-5 context layers:
```python
system_prompt = prompts.SYSTEM              # Base prompt
if perf_context:                            # Layer 1: Performance data
    system_prompt += "\n\n" + perf_context
if memory_context:                          # Layer 2: Agent memories
    system_prompt += "\n\n" + memory_context
if exp_context:                             # Layer 3: Active experiments
    system_prompt += "\n\n" + exp_context
if self_voice:                              # Layer 4: User's voice (script_gen only)
    system_prompt += "\n\n" + self_voice
```

Self-voice injection is script_generation only (where voice matters most).
Experiment context goes into all 3 pipeline nodes.

### Pattern: Auto-Proposal from Data

```python
def auto_propose_experiments(user_id):
    # 1. Fetch last 50 posts with engagement data
    # 2. Group by (platform, variable_name, variable_value)
    # 3. For variables with >= 2 values and >= 2 posts each:
    #    - Compare top vs second performer
    #    - If >15% variance, propose experiment
    # 4. Skip if already being tested
    # 5. Max 3 proposals at a time
```

### Pattern: Self-Voice vs Reference Voice

| Feature | `voice_analysis.py` | `self_voice.py` |
|---------|---------------------|-----------------|
| Source | Reference creator collections | User's own published posts |
| Stored in | `collections.voice_dna` | `profiles.self_voice_dna` |
| Purpose | Write like a specific creator | Write like the user |
| Injected as | Creator voice instructions | "YOUR natural voice" |
| Drift check | N/A | Yes — compare against baseline |

### Pattern: Voice Drift Levels

```python
if drift_score < 0.3:
    drift_level = "low"      # Good match
elif drift_score < 0.6:
    drift_level = "medium"   # Some differences
else:
    drift_level = "high"     # Significant divergence
```

### Files Changed

| File | Action |
|------|--------|
| `infra/supabase/migrations/006_experiments.sql` | NEW — experiments table + self_voice_dna columns |
| `apps/api/app/schemas/experiments.py` | NEW — 8 Pydantic models |
| `apps/api/app/services/experiments.py` | NEW — experiment CRUD, lifecycle, conclusion, auto-proposal |
| `apps/api/app/services/self_voice.py` | NEW — self-voice analysis, drift check, formatting |
| `apps/api/app/routers/experiments.py` | NEW — 13 endpoints (experiments + voice) |
| `apps/api/worker/graph/nodes/gap_analysis.py` | MODIFY — added `_fetch_experiment_context()` |
| `apps/api/worker/graph/nodes/hook_lab.py` | MODIFY — added `_fetch_experiment_context()` |
| `apps/api/worker/graph/nodes/script_generation.py` | MODIFY — added `_fetch_experiment_context()` + `_fetch_self_voice_context()` |
| `apps/api/app/main.py` | MODIFY — register experiments router |
| `apps/web/src/lib/api.ts` | MODIFY — experiments + voice API client + types |
| `apps/web/src/app/experiments/page.tsx` | NEW — experiments + voice UI |
| `apps/api/tests/test_experiments.py` | NEW — 60 unit tests |

### Test Count
- Experiment tests: 60
- All unit tests: 357 passed (brand: 74, pipeline: 24, writing_style: 31, embeddings: 31, collections: 28, performance: 52, memory: 57, experiments: 60)

### Reusable Pattern: Adding Pipeline Context Layers

To add a new context layer to pipeline nodes:
1. Add `_fetch_{name}_context(user_id, ...)` helper in each node
2. Use lazy imports inside try/except for graceful fallback
3. Return empty string on any failure
4. Append to system_prompt after existing layers
5. Test: assert context string contains expected marker, assert empty on no user/error

### Gotchas
- `/experiments/auto-propose` must be defined BEFORE `/{experiment_id}` in router (path collision)
- Self-voice uses `gpt-4o` for analysis, `gpt-4o-mini` for drift check (cost savings)
- Self-voice needs minimum 10 published posts
- Drift check requires existing baseline (returns baseline_available=False otherwise)
- Experiment conclusions auto-create memories with status=pending_approval (not active)
- `completed_at` uses raw SQL `"now()"` string — works with Supabase but returns string in mock
- Variant engagement calculation filters out posts with no engagement_rate
- Auto-proposal skips variables already being tested (checks both A/B and B/A order)
