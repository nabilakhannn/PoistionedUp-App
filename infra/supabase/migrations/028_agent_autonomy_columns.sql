-- Migration 028: Add autonomy columns to openclaw_agents
-- These columns were referenced in agent_orchestrator._get_agent_autonomy()
-- but never formally added to the table schema (migration 021).

ALTER TABLE openclaw_agents
  ADD COLUMN IF NOT EXISTS autonomy_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS confidence_threshold FLOAT NOT NULL DEFAULT 0.8,
  ADD COLUMN IF NOT EXISTS auto_execute BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN openclaw_agents.autonomy_enabled
  IS 'Whether the agent can act autonomously on low-risk tasks';
COMMENT ON COLUMN openclaw_agents.confidence_threshold
  IS 'Minimum confidence (0-1) required for autonomous execution';
COMMENT ON COLUMN openclaw_agents.auto_execute
  IS 'Whether agent can auto-execute without user approval';
