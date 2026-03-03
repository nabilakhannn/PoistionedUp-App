-- Migration 032: Pipeline Settings
-- Stores per-user pipeline schedule controls: enabled, interval, run-now flag, last/next run.

CREATE TABLE IF NOT EXISTS pipeline_settings (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    enabled       boolean NOT NULL DEFAULT true,
    interval_hours integer NOT NULL DEFAULT 24 CHECK (interval_hours >= 1),
    run_now       boolean NOT NULL DEFAULT false,   -- set true by UI → VPS picks it up and clears
    last_run_at   timestamptz,
    next_run_at   timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id)   -- one row per user
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_pipeline_settings_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

CREATE TRIGGER trg_pipeline_settings_updated_at
    BEFORE UPDATE ON pipeline_settings
    FOR EACH ROW EXECUTE FUNCTION update_pipeline_settings_updated_at();

-- RLS: users can only see/edit their own row
ALTER TABLE pipeline_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own pipeline settings"
    ON pipeline_settings FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Index
CREATE INDEX idx_pipeline_settings_user_id ON pipeline_settings (user_id);
