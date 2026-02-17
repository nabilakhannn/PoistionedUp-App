# Pattern: LangGraph Pipeline with Interrupts

**Slice:** 6 — LangGraph Pipeline + Checkpoints + Interrupts
**Date:** 2026-02-14

---

## What this pattern does

8-node sequential LangGraph state machine with 3 interrupt points for human-in-the-loop decisions. Uses PostgresSaver for durable checkpointing — interrupted graphs can resume from any point even after server restart.

Pipeline flow:
```
signal_research → gap_analysis → topic_selection(INTERRUPT)
→ hook_lab(LLM + INTERRUPT) → script_generation(3 LLM calls)
→ editor → testing → approval(INTERRUPT) → DONE
```

## Key design decisions

### Sync graph, not async

The worker is synchronous (plain `time.sleep()` polling loop), so we use `PostgresSaver` (sync) not `AsyncPostgresSaver`. The graph nodes are regular functions, not async. This keeps the worker simple and avoids asyncio event loop complexity.

### Mockable LLM client

All nodes get the LLM via `get_llm_client()` from `worker/graph/llm.py`. This returns an `OpenAIClient` by default, but tests call `set_llm_client(mock)` to inject a `MockLLMClient`. The mock uses a response queue — each `chat()` call pops the next pre-configured JSON response.

```python
class LLMClient(Protocol):
    def chat(self, messages, model, temperature, max_tokens, response_format) -> Dict
```

This Protocol-based approach means tests don't need monkeypatching — just call `set_llm_client()`.

### interrupt() replay behavior

When a node calls `interrupt(value)`:
1. The value is sent to the caller (API receives it as interrupt data)
2. Graph execution pauses, checkpoint is saved
3. Node function has NOT returned — its partial state is NOT committed

When resumed with `Command(resume=data)`:
1. The node function **re-executes from the beginning**
2. `interrupt()` immediately returns `data` instead of pausing
3. Any LLM calls before `interrupt()` run again

This means **hook_lab makes 2 LLM calls across its lifecycle**: one during initial execution (then interrupts), one during resume (then completes). Tests must queue mock responses accordingly:
- Phase 1 (fresh run → topic interrupt): 2 responses (signal_research + gap_analysis)
- Phase 2 (resume topic → hook interrupt): 1 response (hook_lab)
- Phase 3 (resume hook → approval interrupt): 6 responses (hook_lab replay + script_gen×3 + editor + testing)
- Phase 4 (resume approval → done): 0 responses

### Resume via settings._resume

No new database columns needed. The resume payload is stored in the existing `settings` JSONB column under a `_resume` key:

1. API receives user selection (e.g., POST /workflows/{id}/topic with `{selected_topic_id: "..."}`)
2. API stores `settings._resume = {selected_topic_id: "..."}` and sets `status = "queued"`
3. Worker picks up the queued workflow, detects `settings._resume`
4. Worker calls `graph.invoke(Command(resume=payload), config)` with the checkpoint thread_id = workflow_id
5. Worker clears `settings._resume` after processing

### Interrupt detection

After `graph.invoke()`, we check for pending interrupts:
```python
graph_state = graph.get_state(config)
for task in getattr(graph_state, "tasks", []):
    if hasattr(task, "interrupts") and task.interrupts:
        interrupt_node = task.name  # "topic_selection", "hook_lab", or "approval"
```

The `task.name` maps to workflow status via `INTERRUPT_STATUS`:
```python
INTERRUPT_STATUS = {
    "topic_selection": "awaiting_topic",
    "hook_lab": "awaiting_hook",
    "approval": "awaiting_approval",
}
```

### Lazy PostgresSaver import

`pipeline.py` imports `PostgresSaver` lazily (inside `get_checkpointer()`) so that code importing `build_graph()` doesn't need `psycopg` installed. Tests use `MemorySaver` from `langgraph.checkpoint.memory` instead.

### Content Pack structure

The script_generation node makes 3 sequential LLM calls and produces:
```python
content_pack = {
    "youtube_long": {title_used, hook, sections[], cta, estimated_duration_min},
    "youtube_shorts": [{title, script, hook, duration_sec}, ...],  # 3 shorts
    "titles": ["...", ...],  # 10 titles
    "description": "...",
    "tags": ["...", ...],
    "pinned_comment": "...",
    "thumbnail_brief": [{concept, text_overlay}, ...],
}
```

### Fallback selections

Both topic_selection and hook_lab handle invalid IDs gracefully — if the user's `selected_topic_id` or `selected_hook_id` doesn't match any candidate, the first candidate (highest scored) is used as fallback.

## Files

| File | Purpose |
|------|---------|
| `worker/graph/state.py` | PipelineState TypedDict + sub-types |
| `worker/graph/llm.py` | LLMClient Protocol, OpenAIClient, parse_json_response |
| `worker/graph/pipeline.py` | Graph compilation, get_checkpointer, create_initial_state |
| `worker/graph/nodes/signal_research.py` | Node 1: research signals via LLM |
| `worker/graph/nodes/gap_analysis.py` | Node 2: 10 topic candidates with scores |
| `worker/graph/nodes/topic_selection.py` | Node 3: interrupt for user pick |
| `worker/graph/nodes/hook_lab.py` | Node 4: generate 7 hooks + interrupt |
| `worker/graph/nodes/script_generation.py` | Node 5: long + 3 shorts + metadata |
| `worker/graph/nodes/editor.py` | Node 6: voice/clarity editing pass |
| `worker/graph/nodes/testing.py` | Node 7: quality checks |
| `worker/graph/nodes/approval.py` | Node 8: interrupt for approve/reject |
| `worker/graph/prompts/*.py` | System/user prompt templates per node |
| `worker/executor.py` | run_pipeline() — invokes graph, saves assets |
| `worker/main.py` | Worker loop with resume detection |
| `worker/lifecycle.py` | Status transitions (added awaiting_* → queued) |
| `app/routers/workflows.py` | 3 resume endpoints (POST /topic, /hook, /approve) |
| `tests/test_pipeline.py` | 30 unit tests with MockLLMClient + MemorySaver |

## API endpoints (new)

| Method | URL | What |
|--------|-----|------|
| POST | `/workflows/{id}/topic` | Submit topic selection (body: `{selected_topic_id}`) |
| POST | `/workflows/{id}/hook` | Submit hook selection (body: `{selected_hook_id}`) |
| POST | `/workflows/{id}/approve` | Submit approval (body: `{decision, feedback}`) |

All three validate that the workflow is in the expected status (409 if wrong), store the payload in `settings._resume`, set status to `queued`, and log an audit event.

## Dependencies

```
langgraph==0.2.62
langgraph-checkpoint-postgres==2.0.12
psycopg[binary]                # needed for PostgresSaver
```

`psycopg-binary` is required because the dev machine doesn't have libpq installed. The binary package includes its own libpq.

## Gotchas

1. **psycopg needs binary variant.** `pip install psycopg` alone fails without system libpq. Must install `psycopg[binary]` for the self-contained binary driver.
2. **PostgresSaver import is lazy.** If you import `build_graph` from `pipeline.py`, it won't fail even without psycopg. Only `get_checkpointer()` triggers the import.
3. **hook_lab replays LLM call on resume.** Because interrupt() is mid-function, the entire node re-executes when resumed. Budget 2× LLM calls for hook_lab in cost estimates.
4. **MemorySaver for tests.** Use `from langgraph.checkpoint.memory import MemorySaver` — no Postgres needed for pipeline tests.
5. **Thread ID = workflow ID.** The LangGraph checkpoint thread_id is the workflow UUID. One checkpoint stream per workflow.
6. **State merging is automatic.** Nodes return only the keys they update. LangGraph merges partial updates into the full PipelineState TypedDict.
7. **status transitions matter.** The `awaiting_*` statuses can only transition to `queued` (via resume endpoint) or `running` (via executor). The lifecycle.py transition map enforces this.
