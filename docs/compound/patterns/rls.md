# Compound Pattern: Row-Level Security (RLS) on Supabase

**Extracted from:** Slice 2 (Schema + RLS Verified)
**Date:** 2026-02-12

---

## Pattern

Every table in the public schema has RLS enabled. Users can only access their own rows.

### Direct ownership tables (user_id column)

Tables: `profiles`, `resources`, `workflows`, `audit_events`, `usage_costs`, `oauth_tokens`

```sql
-- SELECT: user sees own rows
CREATE POLICY "Users can view own [table]"
  ON public.[table] FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- INSERT: user can only insert rows they own
CREATE POLICY "Users can insert own [table]"
  ON public.[table] FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- UPDATE: user can only update own rows
CREATE POLICY "Users can update own [table]"
  ON public.[table] FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- DELETE: user can only delete own rows
CREATE POLICY "Users can delete own [table]"
  ON public.[table] FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

### Indirect ownership tables (via foreign key to owned table)

Tables: `resource_chunks` (via resources), `workflow_snapshots` (via workflows), `content_assets` (via workflows), `workflow_resources_used` (via workflows)

```sql
-- Access through parent table ownership
CREATE POLICY "Users can view own [child_table]"
  ON public.[child_table] FOR SELECT
  TO authenticated
  USING (
    [parent_fk] IN (SELECT id FROM public.[parent_table] WHERE user_id = auth.uid())
  );
```

### Performance tip

For tables with direct `user_id`, add a btree index:

```sql
CREATE INDEX idx_[table]_user_id ON public.[table](user_id);
```

For indirect ownership queries, the subquery pattern is efficient because PostgreSQL optimizes `IN (SELECT ...)` with a semi-join.

### Worker bypass

The background worker uses `SUPABASE_SERVICE_ROLE_KEY` which bypasses all RLS policies. This key must NEVER be exposed to the frontend.

### Storage RLS

Files are stored at `resource-uploads/{user_id}/{resource_id}/{filename}`. RLS checks the first folder matches the authenticated user:

```sql
(storage.foldername(name))[1] = auth.uid()::text
```

---

## Testing pattern

1. Create two test users via `admin.auth.admin.create_user()`
2. Sign in as each to get access tokens
3. Create per-user Supabase clients with `client.postgrest.auth(token)`
4. Insert test data via service-role client (bypasses RLS)
5. Assert: User A's client returns only User A's rows
6. Assert: User A's client never returns User B's rows
7. Assert: Anonymous client (no JWT) returns 0 rows
8. Cleanup: delete test users (cascades all data)

## Gotcha: uuid generation on Supabase cloud

Use `gen_random_uuid()` (built into Postgres 13+), NOT `uuid_generate_v4()`. The `uuid-ossp` extension on Supabase cloud installs into the `extensions` schema, making the function unavailable as `uuid_generate_v4()` in the `public` schema.
