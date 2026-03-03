-- Migration 031: Auto-Publish Engine
-- Adds publishing result columns to scheduled_items for tracking live post URLs and errors
-- Slice 86: Auto-Publish Engine

-- Add publish result tracking columns to scheduled_items
-- published_at and published_url already exist in the table (from migration 009)
-- We only need the new error + attempt tracking columns

ALTER TABLE public.scheduled_items
  ADD COLUMN IF NOT EXISTS publish_error TEXT,
  ADD COLUMN IF NOT EXISTS publish_attempted_at TIMESTAMPTZ;

-- Index for the background job: fast lookup of due scheduled items
-- Partial index only covers rows where status='scheduled' (keeps index small)
CREATE INDEX IF NOT EXISTS idx_scheduled_items_due
  ON public.scheduled_items(user_id, status, scheduled_at)
  WHERE status = 'scheduled';

-- RLS for new columns is inherited from existing scheduled_items policies
-- (users can only see/update their own rows)
