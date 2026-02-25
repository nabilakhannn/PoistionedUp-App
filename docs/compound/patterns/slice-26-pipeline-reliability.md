# Pattern: Pipeline Reliability (Slice 26)

## Context

The 8-node content pipeline calls OpenAI's API at multiple steps. Transient failures (rate limits, timeouts, 502/503 errors) would crash the entire pipeline. Malformed LLM responses (non-JSON, markdown fences, trailing text) would cause `json.JSONDecodeError` in downstream parsing. Individual node failures would propagate up and kill the whole workflow with no useful error info. This slice adds three layers of defense.

## Pattern 1: LLM Call Retry with Exponential Backoff

### Where

- `apps/api/worker/graph/llm.py` → `OpenAIClient.chat()`

### How it works

1. Every `chat()` call wraps the OpenAI API in a retry loop (max 3 retries + 1 initial attempt = 4 total).
2. Only **retryable** errors trigger retries: `RateLimitError`, `APITimeoutError`, `InternalServerError`, `APIConnectionError`.
3. Non-retryable errors (e.g., `AuthenticationError`, `BadRequestError`) raise immediately on first attempt.
4. Delay between retries uses exponential backoff: 1s → 2s → 4s, capped at 16s.
5. If the OpenAI error includes a `Retry-After` header (common for rate limits), that value is used instead of the calculated backoff, also capped at 16s.
6. On success after retry, a log message notes which attempt succeeded.

### Key design decisions

- **Import-time safety**: OpenAI error classes are imported inside `_is_retryable_error()` to avoid hard dependency at module level. If `openai` is not installed, falls back to string matching on the error message.
- **No jitter**: We skip random jitter because these are single-user workflows, not shared API consumers. Backoff alone is sufficient.
- **Cap at 16s**: We never wait more than 16 seconds per retry. If the API is down for longer, we want to fail fast and let the user know.

### Helper functions

```python
_is_retryable_error(exc) -> bool   # Checks if error is transient
_get_retry_delay(attempt, exc) -> float  # Calculates wait time
```

## Pattern 2: Robust JSON Parsing with Custom Error

### Where

- `apps/api/worker/graph/llm.py` → `parse_json_response()`
- `apps/api/worker/graph/llm.py` → `LLMResponseParseError` (custom exception)

### How it works

Three-strategy cascade:

1. **Direct parse**: Try `json.loads(text)` on the trimmed response. Fastest path for clean JSON.
2. **Markdown fence extraction**: Regex search for `` ```json ... ``` `` or `` ``` ... ``` `` blocks. Extracts and parses the content inside.
3. **Bracket matching**: Find the first `{` or `[`, the last matching `}` or `]`, extract that substring and parse it.

If all three strategies fail, raises `LLMResponseParseError` with a preview of the raw content (first 200 chars).

### Edge cases handled

- Empty/whitespace-only responses
- BOM (byte order mark) prefix characters
- JSON wrapped in markdown code fences with or without language tag
- JSON with leading/trailing prose text
- Multiple code fences (uses first match)

### Key design decisions

- **Custom exception**: `LLMResponseParseError` extends `Exception` and stores `raw_content` for debugging. This replaces the raw `json.JSONDecodeError` that callers previously caught.
- **Never returns empty silently**: Empty responses raise immediately rather than returning `{}`. Callers must handle the error explicitly.

## Pattern 3: Node Safety Decorator

### Where

- `apps/api/worker/graph/llm.py` → `safe_node` decorator
- Applied to 6 nodes: `signal_research`, `gap_analysis`, `hook_lab`, `script_generation`, `editor`, `testing`
- NOT applied to: `topic_selection`, `approval` (these are interrupt nodes with different behavior)

### How it works

```python
@safe_node
def signal_research(state: Dict[str, Any]) -> Dict[str, Any]:
    # ... node logic ...
```

The decorator wraps the node function with:

1. **Timing**: Records start time, logs elapsed time on completion.
2. **Error capture**: On exception, returns a dict with `node_error` key containing the node name, error message, error type, and elapsed seconds.
3. **Control flow passthrough**: Explicitly re-raises `WorkflowBudgetExceeded`, `TokenCeilingExceeded`, `KeyboardInterrupt`, and `GraphInterrupt` so they propagate as intended.
4. **State context**: Reads `workflow_id` from the state dict for log correlation.

### CRITICAL: GraphInterrupt passthrough

`GraphInterrupt` inherits from `Exception` (not `BaseException`), so a bare `except Exception` will catch it. The decorator MUST explicitly re-raise it before the generic handler:

```python
except (WorkflowBudgetExceeded, TokenCeilingExceeded, KeyboardInterrupt, GraphInterrupt):
    raise  # These are intentional control flow, never catch them
except Exception as exc:
    # ... structured error handling ...
```

Without this, LangGraph's interrupt/resume mechanism breaks. The pipeline would silently swallow interrupt requests and continue to the next node.

### Executor integration

`apps/api/worker/executor.py` checks for `node_error` in the final pipeline state:

```python
if final_state.get("node_error"):
    error_info = final_state["node_error"]
    # Create snapshot with error details
    # Update workflow status to "failed"
    return "failed"
```

This means a node failure results in a clean "failed" status with a descriptive error, rather than an unhandled exception crashing the worker.

## Testing patterns

### Testing retry logic

Mock the OpenAI client's `chat.completions.create` to raise on first N calls, then succeed:

```python
mock_create = MagicMock(side_effect=[
    RateLimitError("rate limited", response=mock_response, body=None),
    mock_success_response,  # Succeeds on retry
])
```

Use `@patch("time.sleep")` to skip actual delays in tests.

### Testing safe_node

Create a test function decorated with `@safe_node` and assert the return value:

```python
@safe_node
def failing_node(state):
    raise ValueError("test error")

result = failing_node({"workflow_id": "wf-1"})
assert "node_error" in result
assert result["node_error"]["error"] == "test error"
```

### Verifying decorator application

Use `hasattr(func, "__wrapped__")` to check if a node function has been decorated:

```python
@pytest.mark.parametrize("module_path,func_name", [
    ("worker.graph.nodes.signal_research", "signal_research"),
    # ...
])
def test_node_is_wrapped(self, module_path, func_name):
    mod = importlib.import_module(module_path)
    func = getattr(mod, func_name)
    assert hasattr(func, "__wrapped__")
```

## Anti-patterns to avoid

1. **Don't catch `GraphInterrupt` in the safety decorator**. It breaks LangGraph's interrupt/resume flow. Always re-raise it.
2. **Don't retry `AuthenticationError` or `BadRequestError`**. These are permanent failures that retrying will not fix. Only retry transient errors.
3. **Don't return `{}` on parse failure**. Raising `LLMResponseParseError` forces callers to handle the case explicitly. Silent empty returns hide bugs.
4. **Don't apply `@safe_node` to interrupt nodes** (`topic_selection`, `approval`). These nodes raise `GraphInterrupt` as part of their normal flow. The decorator would add confusing logging for expected behavior.
5. **Don't import OpenAI error classes at module top level** in the retry helper. The import should be deferred so the module can load even if `openai` is not installed (e.g., in test environments with mocks).
