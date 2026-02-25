/**
 * Usage & Cost Tracking API.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface WorkflowCostSummary {
  workflow_id: string;
  goal_text: string;
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  step_count: number;
  created_at: string | null;
}

export interface UsageSummary {
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_calls: number;
  workflow_count: number;
  daily_workflows_used: number;
  daily_workflow_cap: number;
  daily_tokens_used: number;
  daily_token_cap: number;
  period_costs: {
    daily: number;
    weekly: number;
    monthly: number;
  };
  workflows: WorkflowCostSummary[];
}

export interface DailyUsage {
  date: string;
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  call_count: number;
}

export interface CapStatus {
  daily_workflows_used: number;
  daily_workflow_cap: number;
  remaining: number;
  at_limit: boolean;
  daily_tokens_used: number;
  daily_token_cap: number;
  token_cap_remaining: number;
  token_cap_at_limit: boolean;
}

// ── API Methods ──────────────────────────────────────────

export const usageApi = {
  getSummary: (brandId?: string) => {
    const params = new URLSearchParams();
    if (brandId) params.set("brand_id", brandId);
    const qs = params.toString();
    return apiFetch<UsageSummary>(`/usage${qs ? `?${qs}` : ""}`);
  },

  getDaily: (days: number = 30, brandId?: string) => {
    const params = new URLSearchParams();
    params.set("days", String(days));
    if (brandId) params.set("brand_id", brandId);
    return apiFetch<DailyUsage[]>(`/usage/daily?${params.toString()}`);
  },

  getCap: () => apiFetch<CapStatus>("/usage/cap"),
};
