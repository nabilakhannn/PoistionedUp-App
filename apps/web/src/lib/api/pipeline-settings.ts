import { apiFetch } from "./client";

export interface PipelineSettings {
  enabled: boolean;
  interval_hours: number;
  run_now: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  monthly_budget_usd: number;
}

export interface PipelineHealth {
  last_run_at: string | null;
  next_run_at: string | null;
  pipeline_enabled: boolean;
  success_count_24h: number;
  failed_count_24h: number;
  avg_duration_ms: number;
  current_status: "idle" | "running" | "error";
}

export const pipelineSettingsApi = {
  get: (): Promise<PipelineSettings> =>
    apiFetch("/pipeline/settings"),

  update: (data: { enabled?: boolean; interval_hours?: number }): Promise<PipelineSettings> =>
    apiFetch("/pipeline/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  runNow: (): Promise<PipelineSettings> =>
    apiFetch("/pipeline/run-now", { method: "POST" }),

  getApprovalsCount: (): Promise<{ count: number }> =>
    apiFetch("/pipeline/approvals/count"),

  getHealth: (): Promise<PipelineHealth> =>
    apiFetch("/pipeline/health"),
};
