import { apiFetch } from "./client";

export interface AgentRun {
  id: string;
  agent_id: string;
  task_type: string;
  status: "running" | "completed" | "failed";
  prompt_summary: string | null;
  result_summary: string | null;
  model_used: string | null;
  total_tokens: number;
  tool_calls_count: number;
  duration_ms: number | null;
  brand_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface LedgerEntry {
  id: string;
  agent_id: string;
  action_type: "tool_call" | "decision" | "output" | "error";
  action_description: string;
  tool_name: string | null;
  tool_input_summary: string | null;
  tool_result_summary: string | null;
  tokens_used: number;
  created_at: string;
}

export interface LedgerSummary {
  days: number;
  total_runs: number;
  completed: number;
  failed: number;
  total_tokens: number;
  avg_tokens_per_run: number;
  total_tool_calls: number;
  avg_duration_ms: number;
}

export const ledgerApi = {
  listRuns: (params?: { limit?: number; offset?: number; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    if (params?.status) qs.set("status", params.status);
    const q = qs.toString();
    return apiFetch<AgentRun[]>(`/ledger/runs/${q ? `?${q}` : ""}`);
  },

  getRunEntries: (runId: string) =>
    apiFetch<LedgerEntry[]>(`/ledger/runs/${runId}/entries`),

  getAgentRuns: (agentId: string, limit?: number) => {
    const qs = limit ? `?limit=${limit}` : "";
    return apiFetch<AgentRun[]>(`/ledger/agents/${agentId}/runs${qs}`);
  },

  getSummary: (days?: number) => {
    const qs = days ? `?days=${days}` : "";
    return apiFetch<LedgerSummary>(`/ledger/summary${qs}`);
  },
};
