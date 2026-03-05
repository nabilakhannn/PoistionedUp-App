-- Migration 039: Journal Usage Tracking + Pin Control
-- Adds: times_used, last_used_at, pinned to experience_journal
-- Adds: increment_journal_usage() RPC for atomic counter update

-- ── 1. New columns ─────────────────────────────────────────────────────────

ALTER TABLE experience_journal
  ADD COLUMN IF NOT EXISTS times_used   INT          NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS pinned       BOOLEAN      NOT NULL DEFAULT false;

-- ── 2. Indexes ─────────────────────────────────────────────────────────────

-- Pipeline selection: pinned first, then least-used, then oldest
CREATE INDEX IF NOT EXISTS experience_journal_selection
  ON experience_journal(user_id, brand_id, pinned DESC, times_used ASC, created_at ASC);

-- ── 3. Atomic increment RPC ────────────────────────────────────────────────
-- Called by pipeline after Phase 2 completes to track which entries were used.
-- SECURITY DEFINER so it bypasses RLS (called by backend service role).

CREATE OR REPLACE FUNCTION increment_journal_usage(entry_ids UUID[])
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  UPDATE experience_journal
  SET
    times_used   = times_used + 1,
    last_used_at = now()
  WHERE id = ANY(entry_ids);
$$;
