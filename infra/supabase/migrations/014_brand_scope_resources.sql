-- ============================================================
-- 014_brand_scope_resources.sql -- Add brand_id to resources + collections
--
-- Completes the multi-brand wiring started in 012. Resources
-- and collections were the last two user-facing tables without
-- brand_id. This migration adds the column, backfills existing
-- rows, and creates indexes.
-- ============================================================


-- ============================================================
-- 1. Add brand_id to resources
-- ============================================================
ALTER TABLE public.resources
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_resources_brand_id
  ON public.resources(brand_id)
  WHERE brand_id IS NOT NULL;


-- ============================================================
-- 2. Add brand_id to collections
-- ============================================================
ALTER TABLE public.collections
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_collections_brand_id
  ON public.collections(brand_id)
  WHERE brand_id IS NOT NULL;


-- ============================================================
-- 3. Backfill existing rows with user's default brand
-- ============================================================

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.resources r
SET brand_id = db.brand_id
FROM default_brands db
WHERE r.user_id = db.user_id
  AND r.brand_id IS NULL;

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.collections c
SET brand_id = db.brand_id
FROM default_brands db
WHERE c.user_id = db.user_id
  AND c.brand_id IS NULL;


-- ============================================================
-- 4. Done
-- ============================================================
-- brand_id is NULLABLE to match the pattern from 012.
-- Once all API code passes brand_id, a future migration can
-- add NOT NULL constraints.
