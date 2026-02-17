-- ============================================================
-- 010_asset_versioning.sql -- Content Asset Version History
--
-- Adds is_latest flag so old versions are preserved when assets
-- are edited or content is regenerated. Default query returns
-- only the latest version; version history is available via API.
-- ============================================================


-- 1. Add is_latest column
-- ============================================================
ALTER TABLE public.content_assets
  ADD COLUMN IF NOT EXISTS is_latest BOOLEAN NOT NULL DEFAULT TRUE;

-- Index for fast "give me only latest assets" queries
CREATE INDEX IF NOT EXISTS idx_content_assets_latest
  ON public.content_assets(workflow_id, is_latest)
  WHERE is_latest = TRUE;

-- 2. Add feedback column if it doesn't already exist (some setups may not have it)
-- This stores rejection/edit feedback per version
-- (Already exists from 001_init.sql, but safe to run)
-- ALTER TABLE public.content_assets ADD COLUMN IF NOT EXISTS feedback TEXT;

-- 3. Composite unique constraint: one "latest" per workflow+type+platform combo
-- This prevents bugs where two rows claim to be latest for the same asset type
-- We skip this since multiple assets of the same type are valid (e.g. multiple youtube_short)
