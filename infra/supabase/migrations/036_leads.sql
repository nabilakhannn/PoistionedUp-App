-- Slice 95: Lead Gen CRM
-- Creates leads table with 7-field enrichment, BANT scoring, outreach + sequence storage

CREATE TABLE IF NOT EXISTS leads (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id         UUID NOT NULL,

  -- Basic profile
  full_name        VARCHAR(255) NOT NULL,
  title            VARCHAR(255),
  company          VARCHAR(255),
  linkedin_url     VARCHAR(500),
  company_website  VARCHAR(500),
  location         VARCHAR(255),
  email            VARCHAR(255),
  twitter_handle   VARCHAR(100),

  -- CRM stage
  status           VARCHAR(50) NOT NULL DEFAULT 'cold',
  -- values: 'cold' | 'warm' | 'hot' | 'customer' | 'disqualified'
  source           VARCHAR(50) DEFAULT 'manual',
  -- values: 'manual' | 'generated' | 'imported'

  -- 7-field enrichment model (Cameron Sullivan framework)
  -- From personal LinkedIn: professional_topics, recent_achievements
  -- From company LinkedIn: hiring_signals, pain_points
  -- From company website:  company_changes, industries_served, growth_signals
  enrichment       JSONB DEFAULT '{}',

  -- BANT score (0-4, auto-computed on enrich)
  -- Budget +1: funding/revenue signals present
  -- Authority +1: title is director/VP/C-suite
  -- Need +1: pain_points list non-empty
  -- Timing +1: recent trigger event in last 3 months
  bant_score       INTEGER DEFAULT 0 CHECK (bant_score >= 0 AND bant_score <= 4),

  -- User context (private — never exported)
  notes            TEXT,
  transcript       TEXT,

  -- AI outreach
  icebreaker       TEXT,
  outreach_draft   JSONB DEFAULT '{}',
  -- { linkedin_dm: "", cold_email: { subject: "", body: "" } }

  sequence         JSONB DEFAULT '[]',
  -- [
  --   { label: "Message 1 (Connect)", day: 1, channel: "linkedin", message: "", sent_at: null },
  --   { label: "Message 2 (Day 3 — Value)", day: 3, channel: "linkedin", message: "", sent_at: null },
  --   { label: "Message 3 (Day 7 — CTA)", day: 7, channel: "email", message: "", sent_at: null }
  -- ]

  last_enriched_at TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Dedup: one entry per name+company per brand
  UNIQUE (user_id, brand_id, full_name, company)
);

CREATE INDEX IF NOT EXISTS leads_brand_status ON leads(brand_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS leads_bant         ON leads(brand_id, bant_score DESC);
CREATE INDEX IF NOT EXISTS leads_user         ON leads(user_id, created_at DESC);

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own leads" ON leads FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION update_leads_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_leads_updated_at ON leads;
CREATE TRIGGER trg_leads_updated_at
  BEFORE UPDATE ON leads
  FOR EACH ROW EXECUTE FUNCTION update_leads_updated_at();
