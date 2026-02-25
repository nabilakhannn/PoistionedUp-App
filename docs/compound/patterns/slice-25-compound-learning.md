# Pattern: Compound Learning Loop (Slice 25)

## Context

After a user approves a content workflow, the system should automatically learn from the decisions made during that workflow. This creates a compound learning loop where every approved piece of content makes the AI smarter for the next one.

## Pattern 1: Auto-Record Memories After Workflow Approval

### Where

- Service: `apps/api/app/services/agent_memory.py` → `record_workflow_memories()`
- Hook: `apps/api/worker/executor.py` → called after `final_decision == "approved"`

### How it works

1. After the pipeline reaches the approval node and the user approves, the executor calls `record_workflow_memories()`.
2. The function extracts 5 types of learnable signals from the pipeline state:
   - **Topic choice** (observation) — what topic the user picked and its opportunity score
   - **Hook preference** (preference) — which hook style they selected
   - **Objective + content type combo** (observation) — what goal and format they used
   - **Approval feedback** (preference) — any notes the user gave when approving
   - **Content structure** (content_pattern) — the section layout of the approved pack
3. Each memory is created individually with try/except so one failure does not block others.
4. All memories get `source="workflow_approval"` and `related_post_ids=[workflow_id]` for traceability.

### Key design decisions

- **Graceful failure**: Each memory creation is wrapped in try/except. If one fails, the rest still attempt. The function never raises.
- **brand_id propagation**: The executor fetches `brand_id` from the workflow row and passes it through to every memory created.
- **No client parameter**: The function uses `get_admin_client()` internally (deferred import) rather than accepting a client parameter. This keeps the function signature clean.
- **Default confidence levels**: Topic=0.6, Hook=0.65, Objective=0.5, Feedback=0.75, Structure=0.55. Feedback gets the highest confidence because it is direct user input.

### Testing pattern

When testing `record_workflow_memories()`, mock `app.deps.get_admin_client` (NOT `app.services.agent_memory.get_admin_client`) because `create_memory()` uses a deferred import (`from app.deps import get_admin_client`). The mock target must be the source module, not the consuming module.

```python
@patch("app.deps.get_admin_client")
def test_records_topic_memory(self, mock_admin):
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "mem-1", "content": "test", "memory_type": "observation"}]
    )
    mock_admin.return_value.table.return_value = mock_table
    # ...
```

## Pattern 2: Proactive Advisor Suggestions

### Where

- Service: `apps/api/app/services/advisor.py` → `get_suggestions()`
- Router: `apps/api/app/routers/advisor.py` → `GET /advisor/suggestions`
- Frontend: `apps/web/src/app/content/page.tsx` → suggestions panel on content dashboard

### Architecture (3-tier fallback)

1. **LLM-based suggestions**: Aggregates 5 signal types, sends to GPT-4o-mini, gets structured JSON array back.
2. **Rule-based fallback**: If LLM fails, generates suggestions from simple if/then rules on the signals.
3. **Cold start**: If user has no data at all, returns 2 starter tips.

### Signal sources (5 types)

| Signal | Table | What it provides |
|--------|-------|-----------------|
| Performance | `content_posts` | Average engagement, best hook types, top topics |
| Memories | `agent_memory` | Lesson count, preferences, recent learnings |
| Experiments | `agent_experiments` | Active/completed/proposed counts, winning variants |
| Cadence | `workflows` | Days since last content, workflow frequency |
| Schedule | `scheduled_items` | Upcoming content count, next scheduled date |

### Testing pattern for router endpoints

When the router does `from app.services.advisor import get_suggestions`, patch the reference in the router module, not the service module:

```python
# CORRECT: patches the imported reference in the router
@patch("app.routers.advisor.get_suggestions")

# WRONG: patches the original, but router already imported a reference
@patch("app.services.advisor.get_suggestions")
```

## Anti-patterns to avoid

1. **Don't pass the Supabase client to `record_workflow_memories`**. The function gets its own client via `get_admin_client()`. Passing the executor's client would create a tight coupling.
2. **Don't raise from memory recording**. If memory creation fails, the workflow should still complete successfully. Always wrap in try/except.
3. **Don't mock `app.services.module_name.get_admin_client`** when `get_admin_client` is a deferred import from `app.deps`. Mock the source: `app.deps.get_admin_client`.
