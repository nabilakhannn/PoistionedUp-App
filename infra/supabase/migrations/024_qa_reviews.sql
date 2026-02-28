-- Migration 024: QA Reviews — Content Quality Assurance
--
-- Adds persistent QA review storage with 6-dimension scoring,
-- verdict tracking, revision chains, and RLS protection.

-- ── Table: qa_reviews ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS qa_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    brand_id UUID,

    -- Content reference
    content_ref_type TEXT NOT NULL,
    content_ref_id UUID,
    content_text TEXT NOT NULL,
    platform TEXT,

    -- Scores (0-100 each)
    overall_score INT NOT NULL,
    voice_score INT,
    hook_score INT,
    structure_score INT,
    ai_tell_score INT,
    virality_score INT,
    goal_alignment_score INT,

    -- Verdict & feedback
    verdict TEXT NOT NULL DEFAULT 'pending',
    feedback TEXT,
    issues JSONB DEFAULT '[]'::jsonb,
    risk_flags JSONB DEFAULT '[]'::jsonb,

    -- Revision tracking
    revision_number INT DEFAULT 0,
    previous_review_id UUID REFERENCES qa_reviews(id),

    -- Meta
    reviewed_by TEXT DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT now(),

    -- Constraints
    CONSTRAINT qa_reviews_score_range CHECK (overall_score BETWEEN 0 AND 100),
    CONSTRAINT qa_reviews_verdict_enum CHECK (verdict IN ('pass', 'revise', 'fail', 'pending')),
    CONSTRAINT qa_reviews_ref_type_enum CHECK (
        content_ref_type IN ('scheduled_item', 'deliverable', 'workflow', 'freeform')
    ),
    CONSTRAINT qa_reviews_revision_range CHECK (revision_number BETWEEN 0 AND 5),
    CONSTRAINT qa_reviews_dimension_range CHECK (
        (voice_score IS NULL OR voice_score BETWEEN 0 AND 100) AND
        (hook_score IS NULL OR hook_score BETWEEN 0 AND 100) AND
        (structure_score IS NULL OR structure_score BETWEEN 0 AND 100) AND
        (ai_tell_score IS NULL OR ai_tell_score BETWEEN 0 AND 100) AND
        (virality_score IS NULL OR virality_score BETWEEN 0 AND 100) AND
        (goal_alignment_score IS NULL OR goal_alignment_score BETWEEN 0 AND 100)
    )
);

-- ── Indexes ──────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_qa_reviews_user_created
    ON qa_reviews (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_qa_reviews_content_ref
    ON qa_reviews (content_ref_type, content_ref_id);

CREATE INDEX IF NOT EXISTS idx_qa_reviews_user_verdict
    ON qa_reviews (user_id, verdict);

-- ── RLS ──────────────────────────────────────────────────────────
ALTER TABLE qa_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY qa_reviews_select ON qa_reviews
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY qa_reviews_insert ON qa_reviews
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY qa_reviews_update ON qa_reviews
    FOR UPDATE USING (auth.uid() = user_id);
