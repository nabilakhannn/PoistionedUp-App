-- ============================================================
-- 004_performance_feedback.sql -- Performance Feedback Loop
-- Tracks published content + metrics so the AI learns what
-- works for YOUR audience over time.
-- ============================================================


-- 1. content_posts table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.content_posts (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- What was published
  title                 TEXT NOT NULL,
  content_type          TEXT NOT NULL,     -- youtube_long, linkedin_post, twitter_thread, etc.
  platform              TEXT NOT NULL,     -- youtube, linkedin, instagram, twitter, tiktok, etc.

  -- Content details
  hook_used             TEXT,              -- The actual hook text
  hook_type             TEXT,              -- question, bold_claim, story, statistic, contrarian
  topic                 TEXT,
  topic_category        TEXT,              -- ai_tools, business_strategy, personal_branding, etc.
  language              TEXT DEFAULT 'en',
  content_body          TEXT,              -- Full text of what was published

  -- Links
  workflow_id           UUID,              -- Optional link to the workflow that generated it
  collection_id         UUID REFERENCES public.collections(id) ON DELETE SET NULL,
  published_url         TEXT,
  published_at          TIMESTAMPTZ,
  day_of_week           TEXT,              -- monday, tuesday, etc. (for day-of-week analysis)

  -- Metrics (manually entered, updated over time)
  views                 INT,
  likes                 INT,
  comments              INT,
  shares                INT,
  saves                 INT,
  watch_time_seconds    INT,
  click_through_rate    FLOAT,
  impressions           INT,
  reach                 INT,
  subscribers_gained    INT,

  -- Calculated fields (set by API)
  engagement_rate       FLOAT,
  performance_tier      TEXT CHECK (performance_tier IN (
    'viral', 'above_average', 'average', 'below_average', 'flop'
  )),

  -- AI analysis (why it performed well/poorly)
  agent_analysis        JSONB NOT NULL DEFAULT '{}'::jsonb,

  tags                  TEXT[] DEFAULT '{}',
  metadata              JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.content_posts ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_content_posts_user_id
  ON public.content_posts(user_id);

CREATE INDEX IF NOT EXISTS idx_content_posts_platform
  ON public.content_posts(user_id, platform);

CREATE INDEX IF NOT EXISTS idx_content_posts_tier
  ON public.content_posts(user_id, performance_tier)
  WHERE performance_tier IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_content_posts_published_at
  ON public.content_posts(user_id, published_at DESC)
  WHERE published_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_content_posts_topic_category
  ON public.content_posts(user_id, topic_category)
  WHERE topic_category IS NOT NULL;

-- Updated_at trigger
CREATE TRIGGER set_content_posts_updated_at
  BEFORE UPDATE ON public.content_posts
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 2. RLS Policies
-- ============================================================
CREATE POLICY "Users can view own content posts"
  ON public.content_posts FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own content posts"
  ON public.content_posts FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own content posts"
  ON public.content_posts FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own content posts"
  ON public.content_posts FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
