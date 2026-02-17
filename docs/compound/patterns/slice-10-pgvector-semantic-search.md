# Slice 10: pgvector Semantic Search + AI Memory

## Pattern: Embedding-Powered Knowledge Retrieval

### Problem
The AI features (brand chat, content pipeline, suggest endpoint) don't use the user's
uploaded resources (PDFs, workshop transcripts, templates). All knowledge sits in
`resource_chunks.chunk_text` but is never retrieved. Pipeline nodes have explicit
`# TODO: Fetch gold resources` placeholders.

### Solution: pgvector + OpenAI Embeddings
1. Enable pgvector extension in Supabase (built-in, just needs activation)
2. Add `embedding vector(1536)` column to existing `resource_chunks` table
3. Embed chunks at ingestion time using OpenAI `text-embedding-3-small`
4. Search via cosine similarity using Supabase RPC function
5. Auto-inject relevant context into every AI interaction

### Architecture Pattern: Lazy-Import Embedding Service

```python
# In brand_chat.py — lazy import prevents circular deps and test breakage
def get_relevant_context(user_message: str, user_id: str) -> str:
    try:
        from app.services.embeddings import search_similar_chunks, format_chunks_as_context
        chunks = search_similar_chunks(user_message, user_id, limit=3, threshold=0.7)
        return format_chunks_as_context(chunks)
    except Exception:
        return ""  # Graceful degradation — works without embeddings
```

**Key insight**: Every integration point uses try/except with graceful fallback.
If embeddings are unavailable (missing extension, API key, or network issue),
the system continues working — just without resource context.

### Database Pattern: Supabase RPC for Vector Search

```sql
CREATE OR REPLACE FUNCTION match_resource_chunks(
  query_embedding vector(1536),
  match_user_id UUID,
  match_count INT DEFAULT 5,
  match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (id UUID, resource_id UUID, chunk_index INT, chunk_text TEXT,
               metadata JSONB, similarity FLOAT)
```

Called via Supabase client: `admin.rpc("match_resource_chunks", {...})`

The function joins `resource_chunks` with `resources` to filter by `user_id`,
ensuring users only search their own knowledge base.

### Pipeline Integration Pattern: Shared `_fetch_relevant_resources`

Each pipeline node gets an identical helper:
```python
def _fetch_relevant_resources(query: str, user_id: str) -> str:
    if not user_id:
        return "No user context available for resource search."
    try:
        from app.services.embeddings import search_similar_chunks, format_chunks_as_context
        chunks = search_similar_chunks(query, user_id, limit=5)
        context = format_chunks_as_context(chunks)
        return context if context else "No relevant resources found."
    except Exception:
        return "No relevant resources found."
```

Three nodes use this: `gap_analysis`, `script_generation`, `testing`.
Each passes different query text based on its context:
- gap_analysis → `goal_text`
- script_generation → topic title + audience pain
- testing → content title

### Ingestion Pattern: Embed After Chunk Storage

```python
# In _create_chunks (resources.py) — after admin.table("resource_chunks").insert(rows)
try:
    from app.services.embeddings import embed_and_store_chunks
    embed_and_store_chunks(resource_id, chunks)
except Exception:
    logging.warning("Embedding generation failed — chunks stored without embeddings")
```

Chunks are always stored first. Embedding is a secondary step that can fail
without losing the text data. Backfill script handles the catch-up.

### Context Injection Pattern: System Prompt Append

```python
if resource_context:
    system += (
        "\n\n--- RELEVANT KNOWLEDGE FROM USER'S UPLOADED RESOURCES ---\n"
        "Use these excerpts to inform your coaching. Reference specific "
        "frameworks, examples, or insights when relevant:\n\n"
        + resource_context
    )
```

Resource context goes at the end of the system prompt, clearly labeled.
This ensures the LLM can reference it but doesn't confuse it with the
main instructions.

### Files Changed
- `infra/supabase/migrations/002_vector_search.sql` — pgvector, embedding column, IVFFlat index, brand_chats table, RPC function
- `apps/api/app/services/embeddings.py` — embedding generation, batch, search, storage, backfill, context formatting
- `apps/api/app/services/ingestion.py` — (unchanged, embedding wired in resources.py)
- `apps/api/app/routers/resources.py` — add embedding after chunk storage
- `apps/api/app/services/brand_chat.py` — `get_relevant_context()`, updated `build_chat_messages()` with `resource_context` param
- `apps/api/app/routers/brand.py` — call `get_relevant_context()` in chat + suggest endpoints
- `apps/api/worker/graph/nodes/gap_analysis.py` — replaced TODO with `_fetch_relevant_resources`
- `apps/api/worker/graph/nodes/script_generation.py` — replaced TODO with `_fetch_relevant_resources`
- `apps/api/worker/graph/nodes/testing.py` — replaced TODO with `_fetch_relevant_resources`
- `apps/api/tests/test_embeddings.py` — 31 unit tests

### Test Count
- Embedding tests: 31
- All unit tests: 160 passed (brand: 74, pipeline: 24, writing_style: 31, embeddings: 31)

### Gotchas
- Python 3.9: use `Optional[str]` not `str | None` (same as always)
- IVFFlat index needs `lists` parameter — use 100 for < 100K rows
- Supabase pgvector is built-in on cloud but needs `CREATE EXTENSION` to enable
- `text-embedding-3-small` costs $0.02/1M tokens — negligible even at scale
- All embedding integrations use try/except — system works without embeddings
- Pipeline nodes have `user_id` in state (verified in `worker/graph/state.py:64`)
- brand_chats table was used in code but missing from migrations — now formalized
- Lazy imports prevent test breakage when OpenAI/psycopg unavailable
- Backfill function processes in batches of 100 to stay within API limits
- Empty strings replaced with "empty" before sending to OpenAI (rejects empty)
