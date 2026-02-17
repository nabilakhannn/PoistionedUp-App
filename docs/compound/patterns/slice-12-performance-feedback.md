# Slice 12: Performance Feedback Loop

## Pattern: Closed-Loop Performance Data → AI Pipeline Injection

### Problem
Content generation is one-directional — the AI never learns what works for YOUR
specific audience. Every piece of content is generated at the same quality level
because the agent has no feedback signal.

### Solution: Performance Feedback Loop
1. `content_posts` table tracks published content + metrics
2. Analytics engine calculates tiers relative to YOUR averages (not generic benchmarks)
3. Pattern detection auto-discovers what works (hook types, topics, posting days)
4. Performance context injected into every pipeline node's system prompt
5. AI analysis explains why individual posts succeeded or failed

### Architecture Pattern: Relative Performance Tiers

```python
# Tiers are relative to YOUR average, not absolute numbers
TIER_THRESHOLDS = {
    "viral": 3.0,           # 3x+ your average
    "above_average": 1.5,   # 1.5x - 3x
    "average_high": 0.7,    # 0.7x - 1.5x
    "below_average": 0.3,   # 0.3x - 0.7x
    # Below 0.3x = "flop"
}

# Need MIN_POSTS_FOR_TIERS (5) before tiers are meaningful
# Before that, all posts return tier=None
```

**Key insight**: A creator with 500 avg views who gets 1500 views is "viral" for
THEM. Absolute numbers don't matter — relative performance does.

### Pattern: Graceful Performance Context Injection

```python
def _fetch_performance_context(user_id: str, platform: str = "") -> str:
    """Same pattern in 4 places: gap_analysis, hook_lab, script_gen, brand_chat."""
    if not user_id:
        return ""
    try:
        from app.deps import get_admin_client
        admin = get_admin_client()
        resp = admin.table("content_posts").select("*").eq("user_id", user_id)...
        posts = resp.data if resp.data else []
        if not posts:
            return ""
        from app.services.performance_analytics import get_performance_context
        return get_performance_context(posts, platform=platform)
    except Exception:
        return ""  # Graceful fallback — never break content generation
```

Injected into system prompts (not user prompts):
```python
system_prompt = prompts.SYSTEM
if perf_context:
    system_prompt += "\n\n" + perf_context
```

### Pattern: Auto-Detect Patterns from Data

```python
def detect_patterns(posts, by_hook, by_topic, by_day):
    # Hook comparison: "story hooks outperform question hooks by 2.3x"
    # Topic comparison: "Your audience engages most with ai_tools content"
    # Day comparison: "Posts on monday outperform friday by 1.5x"
    # Only detects patterns with >= 2 data points per group
    # Confidence scales with data volume: min(0.9, 0.5 + len(posts) * 0.02)
```

### Performance Context Format for LLM

```
--- YOUR CONTENT PERFORMANCE DATA ---
Based on 15 published posts:
Average engagement rate: 5.2%
Average views: 8500

TOP PERFORMING HOOKS (use these as inspiration):
  - Story hooks are magic
  - LinkedIn hot take on AI

HOOKS THAT FLOPPED (avoid these patterns):
  - Generic post title

BEST PERFORMING TOPICS:
  - ai_tools (5 posts, avg engagement: 6.8%)
  - storytelling (3 posts, avg engagement: 5.5%)

DETECTED PATTERNS:
  - story hooks outperform question hooks by 2.3x
  - Your audience engages most with ai_tools content

Best posting day: monday
```

### Float Boundary Gotcha

```python
# 0.15 / 0.05 = 2.9999999999999996 in Python (not 3.0!)
# Tests should use values clearly above thresholds, not at boundaries
# e.g., 0.20 / 0.05 = 4.0 for viral (safely above 3.0x)
```

### Files Changed
- `infra/supabase/migrations/004_performance_feedback.sql` — content_posts table, RLS, indexes
- `apps/api/app/schemas/performance.py` — 10 Pydantic models
- `apps/api/app/services/performance_analytics.py` — Core analytics engine (tier calc, aggregation, patterns, LLM context)
- `apps/api/app/routers/performance.py` — 6 endpoints (CRUD + analytics + AI analysis)
- `apps/api/worker/graph/nodes/gap_analysis.py` — Added `_fetch_performance_context()`, inject into system prompt
- `apps/api/worker/graph/nodes/hook_lab.py` — Added `_fetch_performance_context()`, inject into system prompt
- `apps/api/worker/graph/nodes/script_generation.py` — Added `_fetch_performance_context()`, inject into system prompt
- `apps/api/app/services/brand_chat.py` — Added `_fetch_performance_context()`, `performance_context` param in `build_chat_messages()`
- `apps/api/app/routers/brand.py` — Wire performance context into brand chat
- `apps/api/app/main.py` — Register performance router
- `apps/web/src/lib/api.ts` — Performance API client + types
- `apps/web/src/app/performance/page.tsx` — Performance tracker UI (posts list, analytics, log form)
- `apps/api/tests/test_performance.py` — 52 unit tests

### Test Count
- Performance tests: 52
- All unit tests: 240 passed (brand: 74, pipeline: 24, writing_style: 31, embeddings: 31, collections: 28, performance: 52)

### Gotchas
- Float division boundary: 0.15/0.05 ≠ 3.0 in Python — use values clearly above thresholds in tests
- MIN_POSTS_FOR_TIERS = 5: tiers return None until user has enough data
- Performance context is always optional — try/except returns "" on any failure
- Lazy imports in pipeline nodes to avoid circular deps with app.services
- Analytics endpoint must be defined BEFORE `/{post_id}` in router to avoid path collision
- Engagement rate = (likes+comments+shares+saves)/views — can be None if no views
- Day of week is stored as lowercase string, entered by user
