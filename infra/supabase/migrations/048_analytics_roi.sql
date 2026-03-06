-- Migration 048: Analytics & ROI Dashboard
-- Adds deal_value for revenue tracking on client deliverables.

-- 1. deal_value on agent_deliverables (nullable; only set for client proposals)
ALTER TABLE agent_deliverables
  ADD COLUMN IF NOT EXISTS deal_value DECIMAL(12,2);

-- 2. Index for revenue aggregation queries
CREATE INDEX IF NOT EXISTS idx_deliverables_revenue
  ON agent_deliverables(user_id, proposal_status, deal_value)
  WHERE deal_value IS NOT NULL;
