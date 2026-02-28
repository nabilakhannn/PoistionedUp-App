-- ============================================================
-- 012_personal_brands.sql -- Multi-Brand Architecture
--
-- Moves brand data from the 1:1 profiles table into a new
-- personal_brands table (1 user → many brands). Every downstream
-- feature (chats, workflows, memory, experiments, posts, schedule)
-- gets scoped by brand_id.
-- ============================================================


-- ============================================================
-- 1. New table: personal_brands
-- ============================================================
CREATE TABLE IF NOT EXISTS public.personal_brands (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  description  TEXT,
  profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.personal_brands ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_personal_brands_user_id
  ON public.personal_brands(user_id);

CREATE INDEX IF NOT EXISTS idx_personal_brands_user_active
  ON public.personal_brands(user_id, is_active)
  WHERE is_active = TRUE;

CREATE TRIGGER set_personal_brands_updated_at
  BEFORE UPDATE ON public.personal_brands
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- RLS policies
CREATE POLICY "Users can view own brands"
  ON public.personal_brands FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own brands"
  ON public.personal_brands FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own brands"
  ON public.personal_brands FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own brands"
  ON public.personal_brands FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);


-- ============================================================
-- 2. Migrate existing profile data into personal_brands
-- ============================================================
-- For every user that has non-empty profile_json, create a
-- "My Brand" row so existing data is not lost.
INSERT INTO public.personal_brands (user_id, name, profile_json, created_at, updated_at)
SELECT
  user_id,
  'My Brand',
  profile_json,
  created_at,
  updated_at
FROM public.profiles
WHERE profile_json IS NOT NULL
  AND profile_json != '{}'::jsonb
ON CONFLICT DO NOTHING;


-- ============================================================
-- 3. Add brand_id columns to downstream tables (nullable first)
-- ============================================================

-- 3a. brand_chats
ALTER TABLE public.brand_chats
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE CASCADE;

-- 3b. workflows
ALTER TABLE public.workflows
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

-- 3c. content_posts
ALTER TABLE public.content_posts
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

-- 3d. agent_memory
ALTER TABLE public.agent_memory
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

-- 3e. agent_experiments
ALTER TABLE public.agent_experiments
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

-- 3f. scheduled_items
ALTER TABLE public.scheduled_items
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

-- 3g. audit_events (optional, for filtering)
ALTER TABLE public.audit_events
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

-- 3h. usage_costs (optional, for reporting)
ALTER TABLE public.usage_costs
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;


-- ============================================================
-- 4. Backfill brand_id on existing rows
-- ============================================================
-- Link existing rows to each user's first (default) brand.
-- Uses a CTE to pick the earliest personal_brands row per user.

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.brand_chats bc
SET brand_id = db.brand_id
FROM default_brands db
WHERE bc.user_id = db.user_id
  AND bc.brand_id IS NULL;

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.workflows w
SET brand_id = db.brand_id
FROM default_brands db
WHERE w.user_id = db.user_id
  AND w.brand_id IS NULL;

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.content_posts cp
SET brand_id = db.brand_id
FROM default_brands db
WHERE cp.user_id = db.user_id
  AND cp.brand_id IS NULL;

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.agent_memory am
SET brand_id = db.brand_id
FROM default_brands db
WHERE am.user_id = db.user_id
  AND am.brand_id IS NULL;

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.agent_experiments ae
SET brand_id = db.brand_id
FROM default_brands db
WHERE ae.user_id = db.user_id
  AND ae.brand_id IS NULL;

WITH default_brands AS (
  SELECT DISTINCT ON (user_id) id AS brand_id, user_id
  FROM public.personal_brands
  WHERE is_active = TRUE
  ORDER BY user_id, created_at ASC
)
UPDATE public.scheduled_items si
SET brand_id = db.brand_id
FROM default_brands db
WHERE si.user_id = db.user_id
  AND si.brand_id IS NULL;


-- ============================================================
-- 5. Indexes on brand_id for all modified tables
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_brand_chats_brand_id
  ON public.brand_chats(brand_id);

CREATE INDEX IF NOT EXISTS idx_workflows_brand_id
  ON public.workflows(brand_id);

CREATE INDEX IF NOT EXISTS idx_content_posts_brand_id
  ON public.content_posts(brand_id);

CREATE INDEX IF NOT EXISTS idx_agent_memory_brand_id
  ON public.agent_memory(brand_id);

CREATE INDEX IF NOT EXISTS idx_agent_experiments_brand_id
  ON public.agent_experiments(brand_id);

CREATE INDEX IF NOT EXISTS idx_scheduled_items_brand_id
  ON public.scheduled_items(brand_id);


-- ============================================================
-- 6. Done
-- ============================================================
-- NOTE: brand_id is left NULLABLE for now so existing code
-- continues to work during the transition. Once all API code
-- is updated to always pass brand_id, a follow-up migration
-- can add NOT NULL constraints.
--
-- profiles.profile_json is NOT dropped. It stays as a legacy
-- fallback. New code reads from personal_brands.profile_json.
