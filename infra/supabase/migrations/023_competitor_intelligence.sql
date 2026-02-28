-- Migration 023: Competitor Intelligence
-- Persistent competitor tracking with metrics history, content monitoring,
-- comparison views, and gap analysis for the Competitor Intelligence Dashboard.

-- ── Table: competitors ────────────────────────────────────────
-- Tracks competitor profiles linked to a user (and optionally a brand).

CREATE TABLE IF NOT EXISTS competitors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_id        UUID REFERENCES personal_brands(id) ON DELETE SET NULL,

    name            TEXT NOT NULL,
    platform        TEXT NOT NULL DEFAULT 'website'
                    CHECK (platform IN ('linkedin', 'twitter', 'youtube', 'tiktok', 'instagram', 'website', 'other')),
    profile_url     TEXT NOT NULL,

    -- Profile intel
    positioning     TEXT,
    niche           TEXT,
    estimated_followers INT,
    pricing_tier    TEXT,
    notes           TEXT,
    threat_level    INT NOT NULL DEFAULT 3
                    CHECK (threat_level >= 1 AND threat_level <= 5),

    -- Lifecycle
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'archived')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fast lookup by owner + brand + status
CREATE INDEX IF NOT EXISTS idx_competitors_user_brand_status
    ON competitors(user_id, brand_id, status);

-- RLS
ALTER TABLE competitors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own competitors"
    ON competitors FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users create own competitors"
    ON competitors FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users update own competitors"
    ON competitors FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users delete own competitors"
    ON competitors FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on competitors"
    ON competitors FOR ALL
    USING (auth.role() = 'service_role');


-- ── Table: competitor_metrics ─────────────────────────────────
-- Time-series snapshots of a competitor's key metrics (followers, engagement, etc.).

CREATE TABLE IF NOT EXISTS competitor_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id       UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,

    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    followers           INT,
    engagement_rate     FLOAT,
    post_frequency_weekly FLOAT,
    avg_post_engagement INT,
    top_topic           TEXT,
    source              TEXT NOT NULL DEFAULT 'manual'
                        CHECK (source IN ('manual', 'scan', 'import')),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Time-series queries: latest metrics first
CREATE INDEX IF NOT EXISTS idx_competitor_metrics_comp_time
    ON competitor_metrics(competitor_id, recorded_at DESC);

-- RLS via parent competitor ownership
ALTER TABLE competitor_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own competitor metrics"
    ON competitor_metrics FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM competitors c
            WHERE c.id = competitor_metrics.competitor_id
              AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users create own competitor metrics"
    ON competitor_metrics FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM competitors c
            WHERE c.id = competitor_metrics.competitor_id
              AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users delete own competitor metrics"
    ON competitor_metrics FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM competitors c
            WHERE c.id = competitor_metrics.competitor_id
              AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role full access on competitor_metrics"
    ON competitor_metrics FOR ALL
    USING (auth.role() = 'service_role');


-- ── Table: competitor_content ─────────────────────────────────
-- Tracked content pieces published by competitors.

CREATE TABLE IF NOT EXISTS competitor_content (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id       UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,

    published_at        TIMESTAMPTZ,
    platform            TEXT,
    title               TEXT,
    url                 TEXT,
    content_preview     TEXT,
    topics              TEXT[],
    engagement_count    INT,
    engagement_rate     FLOAT,
    format              TEXT DEFAULT 'post'
                        CHECK (format IN ('post', 'video', 'carousel', 'thread', 'story', 'article', 'other')),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Content feed: most recent first
CREATE INDEX IF NOT EXISTS idx_competitor_content_comp_time
    ON competitor_content(competitor_id, published_at DESC);

-- RLS via parent competitor ownership
ALTER TABLE competitor_content ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own competitor content"
    ON competitor_content FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM competitors c
            WHERE c.id = competitor_content.competitor_id
              AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users create own competitor content"
    ON competitor_content FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM competitors c
            WHERE c.id = competitor_content.competitor_id
              AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users delete own competitor content"
    ON competitor_content FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM competitors c
            WHERE c.id = competitor_content.competitor_id
              AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role full access on competitor_content"
    ON competitor_content FOR ALL
    USING (auth.role() = 'service_role');
