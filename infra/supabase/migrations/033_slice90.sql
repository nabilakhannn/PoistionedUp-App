-- Migration 033: Slice 90 — AI Marketing & Sales Command Center
-- Tables: research_briefs, knowledge_documents, content_stages, experience_journal
-- Alters: agent_memory (embedding), pipeline_settings (budget columns)

-- ── 1. Research Briefs ──────────────────────────────────────────────────────
-- Saves Phase 1 pipeline output to DB so Sales agents can read what Marketing researched.
CREATE TABLE IF NOT EXISTS research_briefs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id      UUID NOT NULL,
  content       TEXT NOT NULL,
  topic_count   INTEGER DEFAULT 3,
  run_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_briefs_brand_created
  ON research_briefs(brand_id, created_at DESC);

ALTER TABLE research_briefs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own research briefs"
  ON research_briefs FOR ALL
  USING (auth.uid() = user_id);

-- ── 2. Knowledge Documents ──────────────────────────────────────────────────
-- Two-tier: scope='system' (app owner, all users inherit) + scope='user' (per brand).
-- Agents read system SOPs first, then user overrides.
CREATE TABLE IF NOT EXISTS knowledge_documents (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES auth.users(id) ON DELETE CASCADE,  -- NULL for system docs
  brand_id     UUID,                                                -- NULL for global user docs
  title        VARCHAR(255) NOT NULL,
  content      TEXT NOT NULL,
  doc_type     VARCHAR(50) NOT NULL DEFAULT 'other',
               -- writing_sop | cold_email | framework | ad_copy | case_study | other
  platform     VARCHAR(50) NOT NULL DEFAULT 'all',
               -- linkedin | youtube | twitter | email | all
  scope        VARCHAR(20) NOT NULL DEFAULT 'user',
               -- 'system' (app owner, readonly for users) | 'user' (per brand)
  agent_scope  TEXT[] DEFAULT '{}',
               -- which agents see this: ['copywriter', 'distributor'] or [] = all
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_docs_user_brand
  ON knowledge_documents(user_id, brand_id);
CREATE INDEX IF NOT EXISTS knowledge_docs_scope
  ON knowledge_documents(scope, platform, doc_type);

ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;

-- System docs: all authenticated users can read
CREATE POLICY "Users read system knowledge docs"
  ON knowledge_documents FOR SELECT
  USING (scope = 'system' OR auth.uid() = user_id);

-- User docs: only owner can write
CREATE POLICY "Users manage own knowledge docs"
  ON knowledge_documents FOR ALL
  USING (auth.uid() = user_id);

-- ── 3. Content Stages ────────────────────────────────────────────────────────
-- Notion-style editable Kanban stages. Users can add/rename/reorder/delete stages.
CREATE TABLE IF NOT EXISTS content_stages (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id     UUID NOT NULL,
  name         VARCHAR(100) NOT NULL,
  color        VARCHAR(50) DEFAULT 'blue',
  position     INTEGER NOT NULL DEFAULT 0,
  stage_type   VARCHAR(20) NOT NULL DEFAULT 'auto',
               -- 'auto' (agent handles) | 'manual' (human reviews)
  agent_id     VARCHAR(100),
               -- which agent handles this stage (if stage_type = 'auto')
  is_default   BOOLEAN DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS content_stages_brand
  ON content_stages(brand_id, position);

ALTER TABLE content_stages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own content stages"
  ON content_stages FOR ALL
  USING (auth.uid() = user_id);

-- ── 4. Experience Journal ────────────────────────────────────────────────────
-- User's real experiences: call recordings, transcripts, notes, case studies.
-- Agents query this before writing to ground content in real experience.
CREATE TABLE IF NOT EXISTS experience_journal (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id     UUID NOT NULL,
  title        VARCHAR(255),
  source_type  VARCHAR(50) NOT NULL DEFAULT 'note',
               -- 'call_recording' | 'transcript' | 'note' | 'case_study'
  raw_content  TEXT NOT NULL,
  insights     JSONB DEFAULT '[]',
               -- extracted key insights: [{title, summary, tags}]
  tags         TEXT[] DEFAULT '{}',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS experience_journal_brand
  ON experience_journal(brand_id, created_at DESC);

ALTER TABLE experience_journal ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own experience journal"
  ON experience_journal FOR ALL
  USING (auth.uid() = user_id);

-- ── 5. Agent Memory — add embedding column ──────────────────────────────────
-- Enables semantic retrieval: top 5 relevant memories per run, not all memories.
-- pgvector already installed via migration 002.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'agent_memory' AND column_name = 'embedding'
  ) THEN
    ALTER TABLE agent_memory ADD COLUMN embedding vector(1536);
    CREATE INDEX agent_memory_embedding_idx
      ON agent_memory USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 100);
  END IF;
END $$;

-- ── 6. Pipeline Settings — add budget columns ────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'pipeline_settings' AND column_name = 'monthly_budget_usd'
  ) THEN
    ALTER TABLE pipeline_settings
      ADD COLUMN monthly_budget_usd DECIMAL(10,2) DEFAULT 20.00,
      ADD COLUMN budget_alert_at    INTEGER DEFAULT 80;
      -- budget_alert_at: send alert when spend reaches this % of budget
  END IF;
END $$;
