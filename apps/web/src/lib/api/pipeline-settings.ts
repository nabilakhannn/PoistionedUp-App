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

  getApprovalsCount: (brandId?: string): Promise<{ count: number }> => {
    const qs = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : "";
    return apiFetch(`/pipeline/approvals/count${qs}`);
  },

  getHealth: (): Promise<PipelineHealth> =>
    apiFetch("/pipeline/health"),
};
