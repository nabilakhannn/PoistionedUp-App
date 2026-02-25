# Pattern: Wire brand_id Into Every Router and Frontend Page

## Context

Multi-brand support was introduced in Slice 21 (migration 012) which added `brand_id` FK columns to most content tables. However, the API routers and frontend were not fully updated to filter by `brand_id`. This pattern covers the systematic process of wiring `brand_id` through every layer.

## The 5-Layer brand_id Wiring Checklist

When adding `brand_id` support to a feature, touch all 5 layers in order:

### 1. Database (migration)

- Add `brand_id UUID REFERENCES personal_brands(id)` column if missing
- Backfill existing rows: `UPDATE table SET brand_id = (SELECT id FROM personal_brands WHERE user_id = table.user_id AND is_default = true)`
- Create index: `CREATE INDEX idx_table_brand ON table(brand_id)`
- Update RLS policies if needed

### 2. Pydantic Schemas

- Add `brand_id: Optional[str] = None` to Create and Summary schemas
- Keep it optional for backward compatibility

### 3. Service Layer

- Add `brand_id: Optional[str] = None` parameter to all public functions
- Apply `.eq("brand_id", brand_id)` filter to Supabase queries when brand_id is provided
- Include `brand_id` in insert payloads when provided

### 4. API Router

- GET/list endpoints: Accept `brand_id` as optional query parameter
- POST/create endpoints: Accept `brand_id` in request body (via schema)
- Apply filter: `query = query.eq("brand_id", brand_id)` only when brand_id is truthy
- Include brand_id in all insert dicts

### 5. Frontend

- `api.ts`: Update API methods to accept optional `brandId` parameter
  - GET requests: Append `?brand_id=${brandId}` or `&brand_id=${brandId}`
  - POST requests: Include `brand_id: brandId` in body
- Page components: Import `useBrand` from `@/lib/brand-context`
  - Destructure `{ brandId, loading: brandLoading }`
  - Guard data loading with `if (brandLoading || !brandId) return`
  - Add `brandId` and `brandLoading` to `useEffect` dependency arrays
  - Pass `brandId` to all API calls

## The Frontend Page Pattern (copy-paste template)

```tsx
import { useBrand } from "@/lib/brand-context";

export default function FeaturePage() {
  const { brandId, loading: brandLoading } = useBrand();

  const loadData = useCallback(async () => {
    if (brandLoading || !brandId) return;
    // API calls with brandId
    const data = await featureApi.list(brandId);
    setData(data);
  }, [brandId, brandLoading]);

  useEffect(() => { loadData(); }, [loadData]);

  // ... render
}
```

## The API.ts Pattern (copy-paste template)

```ts
// GET with brandId
list: async (brandId?: string) => {
  const q = brandId ? `?brand_id=${brandId}` : "";
  return apiFetch<Item[]>(`/items${q}`);
},

// POST with brandId
create: async (data: CreatePayload, brandId?: string) => {
  return apiFetch<Item>("/items", {
    method: "POST",
    body: JSON.stringify({ ...data, brand_id: brandId }),
  });
},
```

## The Router Pattern (copy-paste template)

```python
@router.get("/items")
async def list_items(
    user: CurrentUser,
    brand_id: Optional[str] = Query(None),
):
    sb = get_admin_client()
    query = sb.table("items").select("*").eq("user_id", user.id)
    if brand_id:
        query = query.eq("brand_id", brand_id)
    result = query.order("created_at", desc=True).execute()
    return result.data
```

## Key Decisions

- `brand_id` is always optional for backward compatibility
- Filtering only applied when brand_id is truthy (not None/empty)
- Frontend guards loading with `brandLoading` to avoid fetching before brand context resolves
- All existing data backfilled to user's default brand during migration

## Tables With brand_id (as of Slice 24)

From migration 012: `brand_chats`, `workflows`, `content_posts`, `agent_memory`, `agent_experiments`, `scheduled_items`, `audit_events`, `usage_costs`

From migration 014: `resources`, `collections`
