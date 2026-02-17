# Slice 13: Agent Memory System

## Pattern: Persistent Learning via Semantic Memory + Approval Workflow

### Problem
The AI agent generates content at the same quality level forever because it never
learns from interactions. It can't remember that you prefer short hooks, hate
rhetorical questions, or that story hooks outperform question hooks for YOUR audience.

### Solution: Agent Memory System
1. `agent_memory` table stores typed memories with embeddings
2. 5 memory types: observation, preference, lesson, content_pattern, voice_note
3. Auto-create observations from performance data (viral/flop posts)
4. Auto-create preferences from user editing patterns (LLM analysis)
5. Synthesize observations into lessons (pending user approval)
6. Semantic search retrieves relevant memories before content generation
7. Memory context injected into system prompts alongside performance data

### Architecture Pattern: Typed Memories with Lifecycle

```python
MEMORY_TYPES = [
    "observation",       # Auto-detected: "story hooks get 2x engagement"
    "preference",        # From user edits: "no rhetorical questions"
    "lesson",            # Synthesized: "shift to 70% AI tools content"
    "content_pattern",   # Structure: "story→insight→CTA works best"
    "voice_note",        # Tone: "conversational, first-person style"
]

STATUS_LIFECYCLE = [
    "pending_approval",  # Lessons wait for user sign-off
    "active",            # Used in prompts
    "dismissed",         # User rejected
    "superseded",        # Replaced by newer memory
    "expired",           # No longer relevant
]
```

### Pattern: Memory Context Injection (Same as Performance)

```python
def _fetch_memory_context(user_id: str, context_query: str = "") -> str:
    """Same pattern in 4 places: gap_analysis, hook_lab, script_gen, brand_chat."""
    if not user_id:
        return ""
    try:
        from app.services.agent_memory import get_relevant_memories, format_memories_as_context
        memories = get_relevant_memories(user_id, context_query, limit=10)
        return format_memories_as_context(memories)
    except Exception:
        return ""  # Graceful fallback — never break content generation
```

Injected AFTER performance context:
```python
system_prompt = prompts.SYSTEM
if perf_context:
    system_prompt += "\n\n" + perf_context
if memory_context:
    system_prompt += "\n\n" + memory_context
```

### Pattern: Grouped Context Formatting

```
--- AGENT MEMORY (What I've learned about your content) ---

OBSERVATIONS (What I've noticed about your content):
  - Story hooks get 2x engagement on YouTube [youtube] (confidence: high)

YOUR PREFERENCES (What you've told me you want):
  - Never use rhetorical questions in hooks [youtube] (confidence: high)

STRATEGIC LESSONS (Approved insights about your content strategy):
  - AI tools content outperforms other topics by 3x (confidence: medium)

CONTENT PATTERNS (Structures that work for you):
  - Story → Insight → CTA structure works best [youtube] (confidence: medium)

Use these memories to personalize the content you're generating.
```

### Pattern: Auto-Observation from Metrics

```python
def create_observation_from_metrics(user_id, post):
    # Only for extreme performers (viral or flop)
    if tier == "viral":
        content = f"{hook_type} hooks about {topic} on {platform} went viral..."
        create_memory(memory_type="observation", source="metrics", ...)
    elif tier == "flop":
        content = f"{hook_type} hooks about {topic} significantly underperformed..."
        create_memory(memory_type="observation", source="metrics", ...)
    # average, above_average, below_average → no observation
```

### Pattern: Auto-Observation from Edits

```python
def create_observation_from_edits(user_id, original, edited):
    # Skip trivial edits (< 10% change)
    if abs(orig_len - edit_len) / max(orig_len, 1) < 0.1:
        return None
    # Use LLM (gpt-4o-mini) to detect editing pattern
    # Creates memory_type="preference", source="user_edit"
```

### Pattern: Synthesis (Observations → Lessons)

```python
def synthesize_memories(user_id):
    # Get all active observations (need >= 3)
    # Group by (category, platform)
    # For each group with >= 2 items:
    #   - Use LLM to synthesize into a strategic lesson
    #   - Create lesson with status="pending_approval"
    #   - Mark synthesized observations as "superseded"
```

### Pattern: Semantic Search with Fallback

```python
def get_relevant_memories(user_id, context_query, platform, limit):
    # 1. Generate query embedding
    # 2. Call match_agent_memories RPC (cosine similarity > 0.6)
    # 3. Filter by platform (keep platform=None memories too)
    # 4. Update last_used_at for retrieved memories
    # 5. On ANY failure → _fallback_memory_search (recent by confidence)
```

### Pattern: Mock Supabase Table Chain

```python
def _mock_supabase_table(mock_admin, data):
    """Set up mock that handles any chain of .select().eq().order().execute()"""
    mock_table = MagicMock()
    mock_admin.return_value.table.return_value = mock_table
    for method in ["select", "eq", "insert", "update", "delete", "order", "limit", "is_"]:
        getattr(mock_table, method).return_value = mock_table
    mock_table.execute.return_value.data = data
    return mock_table
```

### Gotcha: Patching Lazy Imports

```python
# WRONG: patching the attribute on the module that doesn't have it at module level
@patch("app.services.agent_memory.get_admin_client")  # AttributeError!

# RIGHT: patch at the source module where it's actually defined
@patch("app.deps.get_admin_client")  # Works because agent_memory does `from app.deps import get_admin_client`
```

### Files Changed
- `infra/supabase/migrations/005_agent_memory.sql` — agent_memory table, RLS, indexes, IVFFlat, match_agent_memories RPC
- `apps/api/app/schemas/memory.py` — 6 Pydantic models
- `apps/api/app/services/agent_memory.py` — Core memory service (CRUD, search, format, auto-create, synthesis)
- `apps/api/app/routers/memory.py` — 8 endpoints (CRUD + pending + approve + synthesize + delete)
- `apps/api/worker/graph/nodes/gap_analysis.py` — Added `_fetch_memory_context()`, inject after perf context
- `apps/api/worker/graph/nodes/hook_lab.py` — Added `_fetch_memory_context()`, inject after perf context
- `apps/api/worker/graph/nodes/script_generation.py` — Added `_fetch_memory_context()`, inject after perf context
- `apps/api/app/services/brand_chat.py` — Added `_fetch_memory_context()`, `memory_context` param in `build_chat_messages()`
- `apps/api/app/routers/brand.py` — Wire memory context into brand chat
- `apps/api/app/main.py` — Register memory router
- `apps/web/src/lib/api.ts` — Memory API client + types
- `apps/web/src/app/memory/page.tsx` — Memory management UI (list, approve, add)
- `apps/api/tests/test_memory.py` — 57 unit tests

### Test Count
- Memory tests: 57
- All unit tests: 297 passed (brand: 74, pipeline: 24, writing_style: 31, embeddings: 31, collections: 28, performance: 52, memory: 57)

### Gotchas
- Patch at `app.deps.get_admin_client`, NOT `app.services.agent_memory.get_admin_client` (lazy import)
- IVFFlat index created at migration time — needs REINDEX after enough data
- Memory embedding uses same model as resources (text-embedding-3-small, 1536 dims)
- Synthesis needs at least 3 observations, grouped by (category, platform)
- Lessons require user approval (pending_approval → active/dismissed)
- Platform filter in search: keep memories where platform matches OR platform is NULL
- last_used_at updated non-critically (try/except, won't break search)
- Memory context stacks with performance context in system prompts
- build_chat_messages now takes 5 params: module, conversation, resource_context, performance_context, memory_context
