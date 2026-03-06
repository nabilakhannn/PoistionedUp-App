-- Slice 111: Pipeline Hardening + Client Portal Expansion
-- Adds proposal_status column for deliverable lifecycle tracking.

-- 1. Proposal status lifecycle column
ALTER TABLE agent_deliverables
  ADD COLUMN IF NOT EXISTS proposal_status TEXT NOT NULL DEFAULT 'draft';
  -- Values: draft | sent | accepted | rejected | closed_won | closed_lost

COMMENT ON COLUMN agent_deliverables.proposal_status IS
  'Client deliverable lifecycle: draft → sent → accepted/rejected → closed_won/closed_lost';

-- 2. Partial index for client deliverable status queries
CREATE INDEX IF NOT EXISTS idx_deliverables_proposal_status
  ON agent_deliverables(user_id, proposal_status)
  WHERE client_brand = true;
