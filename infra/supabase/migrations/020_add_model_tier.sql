-- Migration 020: Add model_tier column to personal_brands
-- Allows users to choose between budget, standard, and premium LLM tiers
-- budget = GPT-4o-mini (cheapest)
-- standard = Claude 3.5 Haiku (balanced)
-- premium = Claude 3.5 Sonnet (best quality)

ALTER TABLE public.personal_brands
  ADD COLUMN IF NOT EXISTS model_tier text NOT NULL DEFAULT 'budget'
  CHECK (model_tier IN ('budget', 'standard', 'premium'));
