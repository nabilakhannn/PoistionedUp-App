-- Migration 044: Story Bank — Slice 109
-- Extends experience_journal (Slice 90) with AI extraction columns.
-- Story Bank = AI extraction layer ON TOP of existing journal.

-- Add AI extraction columns
ALTER TABLE experience_journal
  ADD COLUMN IF NOT EXISTS extracted_stories JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS story_tags TEXT[] DEFAULT '{}';

-- Extend source_type CHECK to include new types for Story Bank
-- (existing types: call_recording, transcript, note, case_study)
ALTER TABLE experience_journal DROP CONSTRAINT IF EXISTS experience_journal_source_type_check;
ALTER TABLE experience_journal ADD CONSTRAINT experience_journal_source_type_check
  CHECK (source_type IN (
    'call_recording', 'transcript', 'note', 'case_study',
    'idea', 'opinion', 'quote', 'take', 'framework'
  ));

-- Index for story search by theme
CREATE INDEX IF NOT EXISTS idx_experience_journal_extracted
  ON experience_journal USING gin (extracted_stories);

-- RLS already exists on experience_journal from Slice 90
