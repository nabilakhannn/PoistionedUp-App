import { apiFetch } from "./client";

export interface ManusTask {
  id: string;
  manus_task_id: string | null;
  workflow_slug: string;
  status: "pending" | "processing" | "completed" | "failed" | "timeout";
  result_text: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export const manusApi = {
  /** Create a new Manus AI task */
  async createTask(data: {
    brand_id: string;
    workflow_slug: string;
    prompt: string;
    mode?: string;
    profile?: string;
  }): Promise<ManusTask> {
    return apiFetch("/manus/task", { method: "POST", body: JSON.stringify(data) });
  },

  /** Poll a Manus task for status updates */
  async pollTask(taskId: string): Promise<ManusTask> {
    return apiFetch(`/manus/task/${taskId}`);
  },
};
