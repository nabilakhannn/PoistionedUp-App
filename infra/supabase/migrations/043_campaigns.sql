-- Slice 108: Campaigns table
-- Tracks campaign lifecycle: planning → active → paused → done

CREATE TABLE IF NOT EXISTS campaigns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_id    UUID NOT NULL REFERENCES personal_brands(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    platforms   TEXT[] DEFAULT ARRAY['linkedin'],
    content_types TEXT[] DEFAULT ARRAY['text'],
    total_pieces  INT NOT NULL DEFAULT 5,
    completed_pieces INT NOT NULL DEFAULT 0,
    approved_pieces  INT NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'planning'
                CHECK (status IN ('planning', 'active', 'paused', 'done')),
    template_id TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for user/brand queries
CREATE INDEX IF NOT EXISTS idx_campaigns_user_brand ON campaigns(user_id, brand_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);

-- RLS
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;

CREATE POLICY campaigns_select ON campaigns
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY campaigns_insert ON campaigns
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY campaigns_update ON campaigns
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY campaigns_delete ON campaigns
    FOR DELETE USING (auth.uid() = user_id);
