/**
 * Goals API client — agent goals that drive autonomous behavior.
 */
import { apiFetch } from "./client";

export interface AgentGoal {
  id: string;
  title: string;
  description: string | null;
  goal_type: string;
  target_value: number;
  target_unit: string;
  current_value: number;
  platform: string | null;
  status: "active" | "paused" | "completed" | "archived";
  priority: string;
  deadline_at: string | null;
  last_evaluated_at: string | null;
  last_action_at: string | null;
  brand_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoalCreate {
  title: string;
  description?: string;
  goal_type: string;
  target_value: number;
  target_unit?: string;
  platform?: string;
  brand_id?: string;
  priority?: string;
  deadline_at?: string;
}

export const goalsApi = {
  list: (params?: { status?: string; brand_id?: string }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.brand_id) sp.set("brand_id", params.brand_id);
    const qs = sp.toString();
    return apiFetch<AgentGoal[]>(`/goals${qs ? `?${qs}` : ""}`);
  },

  create: (data: GoalCreate) =>
    apiFetch<AgentGoal>("/goals", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  get: (goalId: string) => apiFetch<AgentGoal>(`/goals/${goalId}`),

  update: (goalId: string, data: Partial<AgentGoal>) =>
    apiFetch<AgentGoal>(`/goals/${goalId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (goalId: string) =>
    apiFetch(`/goals/${goalId}`, { method: "DELETE" }),

  evaluate: (goalId: string) =>
    apiFetch<{ goal_id: string; current_value: number; on_track: boolean }>(
      `/goals/${goalId}/evaluate`,
      { method: "POST" }
    ),
};
