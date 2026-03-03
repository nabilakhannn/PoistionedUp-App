-- Migration 035: Landing Page Generator (Slice 93)
-- Stores AI-generated landing pages (two-phase: structure + HTML)

CREATE TABLE IF NOT EXISTS generated_landing_pages (
    id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id      UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    brand_id     UUID REFERENCES brands(id) ON DELETE CASCADE,
    title        TEXT NOT NULL DEFAULT 'Untitled Landing Page',
    description  TEXT,
    inspiration_url TEXT,
    page_goal    TEXT,
    target_audience TEXT,
    structure    JSONB,        -- Phase 1 output (section blueprint)
    html_content TEXT,        -- Phase 2 output (full self-contained HTML)
    model_used   TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE generated_landing_pages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own landing pages"
    ON generated_landing_pages FOR ALL
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS generated_landing_pages_brand_created
    ON generated_landing_pages (brand_id, created_at DESC);
