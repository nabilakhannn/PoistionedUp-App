# Slice 11: Knowledge Base Collections + Creator Voice DNA

## Pattern: Hierarchical Content Organization with AI Style Analysis

### Problem
Resources exist as a flat list with tags. Users have content from multiple creators
(Hormozi, Lara Acosta, Gary Vee) but can't organize by creator, search within
one creator's content, or generate content that mimics a specific creator's style.

### Solution: Collections + Voice DNA
1. Collections table as "folders" — each named after a creator
2. Resources optionally belong to one collection via FK
3. Collection-scoped semantic search (search within one creator's content)
4. Voice DNA extraction — LLM analyzes creator's content to build structured style profile
5. Voice DNA formatting — inject style instructions into any LLM prompt

### Architecture Pattern: Two-Phase Query (Supabase PostgREST Limitation)

```python
# PostgREST doesn't support subqueries in .in_(), so we use two queries:
def _get_collection_chunks_via_join(admin, collection_id):
    # Step 1: Get resource IDs in collection
    res_resp = admin.table("resources").select("id").eq("collection_id", collection_id).execute()
    resource_ids = [r["id"] for r in res_resp.data]

    # Step 2: Fetch chunks for those resources
    chunks_resp = admin.table("resource_chunks").select("...").in_("resource_id", resource_ids).execute()
```

**Key insight**: Supabase PostgREST requires explicit two-step queries where
PostgreSQL would allow a subquery. The RPC function (for vector search) can
still use JOINs since it runs as raw SQL.

### Voice DNA Pattern: Sample + Analyze + Cache

```python
# 1. Sample diverse chunks (hooks, middles, endings from different resources)
sampled = _sample_chunks(all_chunks, max_samples=60)

# 2. Send to LLM with structured extraction prompt
response = llm.chat(messages=[...], response_format={"type": "json_object"})

# 3. Cache result in JSONB column (no recompute until user requests)
admin.table("collections").update({"voice_dna": voice_dna}).eq("id", collection_id).execute()
```

The Voice DNA is stored in the `collections.voice_dna` JSONB column.
It's a one-time extraction per analyze-voice request, not recomputed
on every content generation. Re-analyze when new resources are added.

### Voice DNA Format for LLM Prompts

```python
def format_voice_dna_instructions(voice_dna: dict) -> str:
    """Append to any system prompt to enable creator mimicry."""
    # Returns structured block:
    # --- CREATOR VOICE STYLE INSTRUCTIONS ---
    # TONE: Direct and aggressive...
    # SENTENCE STYLE: Short punchy...
    # SIGNATURE PHRASES: "starving crowd", "dream outcome"...
    # EXAMPLE HOOKS: ...
```

### Nullable FK Pattern: Resources Without Collections

```sql
ALTER TABLE public.resources
  ADD COLUMN IF NOT EXISTS collection_id UUID
  REFERENCES public.collections(id) ON DELETE SET NULL;
```

- Resources can exist without a collection (collection_id = NULL)
- Deleting a collection sets resources' collection_id to NULL (ON DELETE SET NULL)
- Resources can be moved between collections by updating collection_id
- Index only on non-NULL values: `WHERE collection_id IS NOT NULL`

### Collection-Scoped Search: Separate RPC Function

```sql
CREATE OR REPLACE FUNCTION match_collection_chunks(
  query_embedding vector(1536),
  match_collection_id UUID,
  ...
) -- Same as match_resource_chunks but JOINs on r.collection_id instead of r.user_id
```

Two RPC functions now:
- `match_resource_chunks` — search all of a user's content
- `match_collection_chunks` — search within one collection

### Files Changed
- `infra/supabase/migrations/003_collections.sql` — collections table, collection_id FK, RLS, scoped search RPC
- `apps/api/app/schemas/collection.py` — VoiceDNA, CRUD models, search models
- `apps/api/app/routers/collections.py` — 9 endpoints (CRUD + voice analysis + scoped search)
- `apps/api/app/services/voice_analysis.py` — Voice DNA extraction, sampling, formatting
- `apps/api/app/services/embeddings.py` — Added `search_collection_chunks()` function
- `apps/api/app/schemas/resource.py` — Added `collection_id` to ResourceCreateNote + ChannelImportRequest
- `apps/api/app/routers/resources.py` — Wire collection_id into all 3 creation endpoints
- `apps/api/app/main.py` — Register collections router
- `apps/web/src/lib/api.ts` — Collections API client
- `apps/web/src/app/knowledge/page.tsx` — Collection grid with create modal
- `apps/web/src/app/knowledge/[id]/page.tsx` — Collection detail with Voice DNA, search, resources
- `apps/api/tests/test_collections.py` — 28 unit tests

### Test Count
- Collection tests: 28
- All unit tests: 188 passed (brand: 74, pipeline: 24, writing_style: 31, embeddings: 31, collections: 28)

### Gotchas
- Supabase PostgREST doesn't support subqueries in `.in_()` — use two-step queries
- Voice DNA analysis needs at least 5 chunks (about 2-3 resources with content)
- `min_items` is deprecated in Pydantic v2 — use `min_length` for list fields
- Lazy imports for `get_llm_client` and `parse_json_response` in voice_analysis.py
- Patch at source module for tests: `@patch("worker.graph.llm.get_llm_client")`
- IVFFlat index only on resources within collections for scoped search
- Collection create/delete doesn't affect resources (ON DELETE SET NULL)
- Voice DNA cached in JSONB — re-analyze is explicit user action, not automatic
