-- ============================================================
-- 009_schedule.sql -- Content Schedule (Kanban + Calendar)
--
-- Tracks content items through a kanban pipeline:
--   draft -> scheduled -> published -> archived
-- Each item can have a scheduled_at date for the calendar view.
-- ============================================================


-- 1. scheduled_items table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.scheduled_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- What content this is
  title           TEXT NOT NULL,
  platform        TEXT NOT NULL,         -- youtube, linkedin, twitter, tiktok, instagram, etc.
  content_type    TEXT NOT NULL,          -- youtube_long, youtube_short, linkedin_post, twitter_post, short_form
  body_preview    TEXT,                   -- First ~200 chars for card preview
  content_json    JSONB NOT NULL DEFAULT '{}'::jsonb,  -- Full content data

  -- Links back to generation
  workflow_id     UUID REFERENCES public.workflows(id) ON DELETE SET NULL,
  asset_id        UUID REFERENCES public.content_assets(id) ON DELETE SET NULL,
  content_post_id UUID REFERENCES public.content_posts(id) ON DELETE SET NULL,

  -- Kanban state
  status          TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'scheduled', 'published', 'archived')),
  column_order    INT NOT NULL DEFAULT 0,  -- Sort position within a column

  -- Calendar
  scheduled_at    TIMESTAMPTZ,             -- When to publish (null = unscheduled draft)
  published_at    TIMESTAMPTZ,             -- When actually published
  published_url   TEXT,                    -- Link to the live post

  -- Display
  color_label     TEXT CHECK (color_label IN (
    'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', NULL
  )),
  notes           TEXT,                    -- Internal notes (not published)

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.scheduled_items ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_scheduled_items_user_id
  ON public.scheduled_items(user_id);

CREATE INDEX IF NOT EXISTS idx_scheduled_items_status
  ON public.scheduled_items(user_id, status, column_order);

CREATE INDEX IF NOT EXISTS idx_scheduled_items_scheduled_at
  ON public.scheduled_items(user_id, scheduled_at)
  WHERE scheduled_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_scheduled_items_platform
  ON public.scheduled_items(user_id, platform);

CREATE INDEX IF NOT EXISTS idx_scheduled_items_workflow
  ON public.scheduled_items(workflow_id)
  WHERE workflow_id IS NOT NULL;

-- Updated_at trigger
CREATE TRIGGER set_scheduled_items_updated_at
  BEFORE UPDATE ON public.scheduled_items
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 2. RLS Policies
-- ============================================================
CREATE POLICY "Users can view own scheduled items"
  ON public.scheduled_items FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own scheduled items"
  ON public.scheduled_items FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own scheduled items"
  ON public.scheduled_items FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own scheduled items"
  ON public.scheduled_items FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);


-- 3. Enable Realtime for live kanban updates
-- ============================================================
DO $$ BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.scheduled_items;
EXCEPTION WHEN duplicate_object THEN
  NULL;
END $$;
