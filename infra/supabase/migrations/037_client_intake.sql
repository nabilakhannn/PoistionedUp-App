-- Slice 97: Client Onboarding Intelligence Wizard
-- client_intake_forms table + is_client_brand flag on personal_brands

-- ── 1. is_client_brand flag on personal_brands ────────────────────────────
ALTER TABLE personal_brands
  ADD COLUMN IF NOT EXISTS is_client_brand BOOLEAN NOT NULL DEFAULT false;

-- ── 2. client_intake_forms ────────────────────────────────────────────────
-- Public shareable form sent to clients before the discovery call.
-- SB creates it; client fills it in at /intake/[share_token] (no auth required).

CREATE TABLE IF NOT EXISTS client_intake_forms (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id            UUID NOT NULL,

  -- 64-char random hex token used in the public share URL
  share_token         VARCHAR(64) UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(32), 'hex'),

  -- Client-filled fields (all optional until submitted)
  client_name         VARCHAR(255),
  business_name       VARCHAR(255),
  industry            VARCHAR(255),
  current_revenue     VARCHAR(100),
  primary_offer       TEXT,
  offer_price         VARCHAR(100),
  secondary_offers    TEXT,
  target_audience     TEXT,
  best_3_clients      TEXT,
  traffic_sources     TEXT,
  funnel_status       TEXT,
  biggest_frustration TEXT,
  goals               TEXT,
  tech_stack          TEXT,
  timeline            VARCHAR(255),
  additional_notes    TEXT,

  -- Lifecycle
  submitted_at        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS intake_forms_user_brand
  ON client_intake_forms(user_id, brand_id, created_at DESC);

CREATE INDEX IF NOT EXISTS intake_forms_token
  ON client_intake_forms(share_token);

ALTER TABLE client_intake_forms ENABLE ROW LEVEL SECURITY;

-- SB manages their own intake forms (authenticated)
CREATE POLICY "Users manage own intake forms" ON client_intake_forms
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Public read by share_token — clients fill it in without auth
CREATE POLICY "Public read by share_token" ON client_intake_forms
  FOR SELECT
  USING (true);
