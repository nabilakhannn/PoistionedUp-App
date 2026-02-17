-- ============================================================
-- 001_init.sql -- Content Orchestrator MVP Schema
-- Source of truth: Content_Orchestrator_MVP_PRD.md (Section 10)
-- ============================================================

-- 0. Extensions
-- ============================================================
-- uuid-ossp not needed: gen_random_uuid() is built into Postgres 13+
CREATE EXTENSION IF NOT EXISTS "pgmq";
-- pgvector deferred until embedding search is needed:
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Helper: auto-update updated_at trigger
-- ============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 2. Tables
-- ============================================================

-- 2a. profiles (1:1 with auth.users)
-- ============================================================
CREATE TABLE public.profiles (
  user_id      UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE TRIGGER set_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 2b. resources
-- ============================================================
CREATE TYPE public.resource_type AS ENUM ('link', 'file', 'note', 'transcript');

CREATE TABLE public.resources (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type         public.resource_type NOT NULL,
  title        TEXT NOT NULL,
  source_url   TEXT,
  tags         TEXT[] NOT NULL DEFAULT '{}',
  is_gold      BOOLEAN NOT NULL DEFAULT FALSE,
  content_text TEXT NOT NULL DEFAULT '',
  storage_path TEXT,  -- Supabase Storage path; null for non-file types
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.resources ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_resources_user_id ON public.resources(user_id);
CREATE INDEX idx_resources_tags ON public.resources USING GIN(tags);
CREATE INDEX idx_resources_is_gold ON public.resources(user_id, is_gold) WHERE is_gold = TRUE;

CREATE TRIGGER set_resources_updated_at
  BEFORE UPDATE ON public.resources
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 2c. resource_chunks
-- ============================================================
CREATE TABLE public.resource_chunks (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_id  UUID NOT NULL REFERENCES public.resources(id) ON DELETE CASCADE,
  chunk_index  INT NOT NULL,
  chunk_text   TEXT NOT NULL,
  -- embedding vector(1536),  -- Enable when pgvector is needed
  metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.resource_chunks ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_resource_chunks_resource_id ON public.resource_chunks(resource_id);
CREATE UNIQUE INDEX idx_resource_chunks_unique ON public.resource_chunks(resource_id, chunk_index);


-- 2d. workflows
-- ============================================================
CREATE TYPE public.workflow_status AS ENUM (
  'queued',
  'running',
  'awaiting_topic',
  'awaiting_hook',
  'awaiting_approval',
  'approved',
  'rejected',
  'failed'
);

CREATE TABLE public.workflows (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status            public.workflow_status NOT NULL DEFAULT 'queued',
  goal_text         TEXT NOT NULL,
  settings          JSONB NOT NULL DEFAULT '{}'::jsonb,
  profile_snapshot  JSONB NOT NULL DEFAULT '{}'::jsonb,
  workflow_plan     JSONB,
  current_step      TEXT,
  active_version    INT NOT NULL DEFAULT 1,
  error_message     TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.workflows ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_workflows_user_id ON public.workflows(user_id);
CREATE INDEX idx_workflows_status ON public.workflows(user_id, status);
CREATE INDEX idx_workflows_created_at ON public.workflows(user_id, created_at DESC);

CREATE TRIGGER set_workflows_updated_at
  BEFORE UPDATE ON public.workflows
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- Enable Supabase Realtime for live status updates to frontend
ALTER PUBLICATION supabase_realtime ADD TABLE public.workflows;


-- 2e. workflow_snapshots
-- ============================================================
CREATE TABLE public.workflow_snapshots (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id  UUID NOT NULL REFERENCES public.workflows(id) ON DELETE CASCADE,
  step_id      TEXT NOT NULL,
  version      INT NOT NULL DEFAULT 1,
  state_json   JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.workflow_snapshots ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_workflow_snapshots_workflow_id ON public.workflow_snapshots(workflow_id);
CREATE INDEX idx_workflow_snapshots_step ON public.workflow_snapshots(workflow_id, step_id);


-- 2f. content_assets
-- ============================================================
CREATE TYPE public.asset_type AS ENUM (
  'youtube_long',
  'youtube_short',
  'title_set',
  'description',
  'tags',
  'pinned_comment',
  'thumbnail_brief',
  'topic_candidates',
  'hook_candidates',
  'test_report'
);

CREATE TYPE public.asset_status AS ENUM ('draft', 'approved', 'rejected');

CREATE TABLE public.content_assets (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id  UUID NOT NULL REFERENCES public.workflows(id) ON DELETE CASCADE,
  version      INT NOT NULL DEFAULT 1,
  type         public.asset_type NOT NULL,
  platform     TEXT NOT NULL DEFAULT 'youtube',
  content_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status       public.asset_status NOT NULL DEFAULT 'draft',
  feedback     TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.content_assets ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_content_assets_workflow_id ON public.content_assets(workflow_id);
CREATE INDEX idx_content_assets_type ON public.content_assets(workflow_id, type);
CREATE INDEX idx_content_assets_version ON public.content_assets(workflow_id, type, version DESC);

CREATE TRIGGER set_content_assets_updated_at
  BEFORE UPDATE ON public.content_assets
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 2g. workflow_resources_used (junction table)
-- ============================================================
CREATE TABLE public.workflow_resources_used (
  workflow_id  UUID NOT NULL REFERENCES public.workflows(id) ON DELETE CASCADE,
  resource_id  UUID NOT NULL REFERENCES public.resources(id) ON DELETE CASCADE,
  usage_type   TEXT NOT NULL CHECK (usage_type IN ('research', 'script', 'both')),
  PRIMARY KEY (workflow_id, resource_id)
);

ALTER TABLE public.workflow_resources_used ENABLE ROW LEVEL SECURITY;


-- 2h. audit_events
-- ============================================================
CREATE TABLE public.audit_events (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  workflow_id  UUID REFERENCES public.workflows(id) ON DELETE SET NULL,
  event_type   TEXT NOT NULL CHECK (event_type IN (
    'workflow_created',
    'workflow_started',
    'topic_selected',
    'hook_selected',
    'approved',
    'rejected',
    'regenerated',
    'failed',
    'exported'
  )),
  payload      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_audit_events_user_id ON public.audit_events(user_id);
CREATE INDEX idx_audit_events_workflow_id ON public.audit_events(workflow_id);
CREATE INDEX idx_audit_events_created_at ON public.audit_events(created_at DESC);


-- 2i. usage_costs
-- ============================================================
CREATE TABLE public.usage_costs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id     UUID NOT NULL REFERENCES public.workflows(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  step_id         TEXT NOT NULL,
  model_name      TEXT NOT NULL,
  input_tokens    INT NOT NULL DEFAULT 0,
  output_tokens   INT NOT NULL DEFAULT 0,
  estimated_cost  NUMERIC(10, 6) NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.usage_costs ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_usage_costs_workflow_id ON public.usage_costs(workflow_id);
CREATE INDEX idx_usage_costs_user_id ON public.usage_costs(user_id);
CREATE INDEX idx_usage_costs_user_daily ON public.usage_costs(user_id, created_at);


-- ============================================================
-- 3. RLS Policies
-- ============================================================

-- 3a. profiles
CREATE POLICY "Users can view own profile"
  ON public.profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
  ON public.profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
  ON public.profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 3b. resources
CREATE POLICY "Users can view own resources"
  ON public.resources FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own resources"
  ON public.resources FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own resources"
  ON public.resources FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own resources"
  ON public.resources FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- 3c. resource_chunks (access via resource ownership)
CREATE POLICY "Users can view own resource chunks"
  ON public.resource_chunks FOR SELECT
  TO authenticated
  USING (
    resource_id IN (SELECT id FROM public.resources WHERE user_id = auth.uid())
  );

CREATE POLICY "Users can insert own resource chunks"
  ON public.resource_chunks FOR INSERT
  TO authenticated
  WITH CHECK (
    resource_id IN (SELECT id FROM public.resources WHERE user_id = auth.uid())
  );

CREATE POLICY "Users can delete own resource chunks"
  ON public.resource_chunks FOR DELETE
  TO authenticated
  USING (
    resource_id IN (SELECT id FROM public.resources WHERE user_id = auth.uid())
  );

-- 3d. workflows
CREATE POLICY "Users can view own workflows"
  ON public.workflows FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own workflows"
  ON public.workflows FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own workflows"
  ON public.workflows FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 3e. workflow_snapshots (access via workflow ownership)
CREATE POLICY "Users can view own workflow snapshots"
  ON public.workflow_snapshots FOR SELECT
  TO authenticated
  USING (
    workflow_id IN (SELECT id FROM public.workflows WHERE user_id = auth.uid())
  );
-- Note: Workers INSERT snapshots via service_role key (bypasses RLS).

-- 3f. content_assets (access via workflow ownership)
CREATE POLICY "Users can view own content assets"
  ON public.content_assets FOR SELECT
  TO authenticated
  USING (
    workflow_id IN (SELECT id FROM public.workflows WHERE user_id = auth.uid())
  );

CREATE POLICY "Users can update own content assets"
  ON public.content_assets FOR UPDATE
  TO authenticated
  USING (
    workflow_id IN (SELECT id FROM public.workflows WHERE user_id = auth.uid())
  );

-- 3g. workflow_resources_used
CREATE POLICY "Users can view own workflow resource usage"
  ON public.workflow_resources_used FOR SELECT
  TO authenticated
  USING (
    workflow_id IN (SELECT id FROM public.workflows WHERE user_id = auth.uid())
  );

-- 3h. audit_events
CREATE POLICY "Users can view own audit events"
  ON public.audit_events FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- 3i. usage_costs
CREATE POLICY "Users can view own usage costs"
  ON public.usage_costs FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);


-- 2j. oauth_tokens (for Google Docs + Notion export)
-- ============================================================
CREATE TABLE public.oauth_tokens (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider        TEXT NOT NULL CHECK (provider IN ('google', 'notion')),
  access_token    TEXT NOT NULL,
  refresh_token   TEXT,
  token_expires_at TIMESTAMPTZ,
  scopes          TEXT[] NOT NULL DEFAULT '{}',
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.oauth_tokens ENABLE ROW LEVEL SECURITY;

CREATE UNIQUE INDEX idx_oauth_tokens_user_provider ON public.oauth_tokens(user_id, provider);

CREATE TRIGGER set_oauth_tokens_updated_at
  BEFORE UPDATE ON public.oauth_tokens
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- RLS: users can only see/manage their own tokens
CREATE POLICY "Users can view own oauth tokens"
  ON public.oauth_tokens FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own oauth tokens"
  ON public.oauth_tokens FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own oauth tokens"
  ON public.oauth_tokens FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own oauth tokens"
  ON public.oauth_tokens FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);


-- ============================================================
-- 4. Service Role Notes
-- ============================================================
-- The worker uses SUPABASE_SERVICE_ROLE_KEY which bypasses RLS.
-- This key must NEVER be exposed to the frontend.
-- No additional grants are needed for the service role.


-- ============================================================
-- 5. Queue Setup (pgmq)
-- ============================================================
SELECT pgmq.create('workflow_jobs');
SELECT pgmq.create('workflow_jobs_dlq');


-- ============================================================
-- 6. Storage Bucket
-- ============================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'resource-uploads',
  'resource-uploads',
  FALSE,
  52428800,  -- 50 MB max file size
  ARRAY[
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
    'text/csv'
  ]
);

-- Storage RLS: files stored as resource-uploads/{user_id}/{resource_id}/{filename}
CREATE POLICY "Users can upload own resources"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'resource-uploads'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

CREATE POLICY "Users can view own resource uploads"
  ON storage.objects FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'resource-uploads'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

CREATE POLICY "Users can delete own resource uploads"
  ON storage.objects FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'resource-uploads'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );
