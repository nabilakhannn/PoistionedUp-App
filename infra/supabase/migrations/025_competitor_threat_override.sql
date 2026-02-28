-- Migration 025: Add threat_level_override to competitors
-- Tracks whether user manually set the threat level (overrides dynamic calculation).
-- When threat_level_override=true, dynamic scoring calculates but does NOT
-- update the stored threat_level value.

ALTER TABLE competitors
  ADD COLUMN IF NOT EXISTS threat_level_override BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN competitors.threat_level_override
  IS 'True if user manually set threat_level; prevents dynamic scoring overwrites';
