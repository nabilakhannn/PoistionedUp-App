import { apiFetch } from "./client";

export interface FormField {
  name: string;
  type: "text" | "textarea" | "select" | "file" | "number";
  label: string;
  options?: string[];
  placeholder?: string;
  required: boolean;
  accept?: string;
}

export interface WorkflowStep {
  name: string;
}

export interface WorkflowInfo {
  slug: string;
  name: string;
  category: string;
  icon: string;
  tags: string[];
  description: string;
  status: "active" | "coming_soon";
  multi_step: boolean;
  steps: WorkflowStep[];
  inputs: FormField[];
  estimated_tokens: number;
  engine: "builtin" | "manus_beneficial";
  enhancements: string[];
}

export interface CategoryInfo {
  name: string;
  icon: string;
  order: number;
}

export interface RegistryResponse {
  categories: Record<string, CategoryInfo>;
  workflows: Record<string, WorkflowInfo>;
}

export interface WorkflowRunResult {
  run_id: string;
  status: "completed" | "failed" | "running";
  content?: string | null;
  error?: string | null;
  engine: string;
  duration_ms: number;
  tokens_used: number;
  model_used: string;
}

export interface WorkflowRun {
  id: string;
  user_id: string;
  brand_id: string;
  workflow_slug: string;
  inputs: Record<string, string>;
  output: string | null;
  status: string;
  engine: string;
  duration_ms: number | null;
  tokens_used: number;
  created_at: string;
}

export const marketplaceApi = {
  /** Get full workflow registry */
  async getRegistry(): Promise<RegistryResponse> {
    return apiFetch("/marketplace/registry");
  },

  /** Run a workflow */
  async runWorkflow(
    slug: string,
    data: {
      brand_id: string;
      inputs: Record<string, string>;
      engine?: string;
      step_index?: number;
      previous_outputs?: string[];
    },
  ): Promise<WorkflowRunResult> {
    return apiFetch(`/marketplace/run/${slug}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /** Get run status */
  async getRunStatus(runId: string): Promise<WorkflowRun> {
    return apiFetch(`/marketplace/runs/${runId}`);
  },

  /** Get run history */
  async getHistory(
    brandId: string,
    workflowSlug?: string,
    limit = 20,
    offset = 0,
  ): Promise<{ runs: WorkflowRun[]; total: number }> {
    const params = new URLSearchParams({
      brand_id: brandId,
      limit: String(limit),
      offset: String(offset),
    });
    if (workflowSlug) params.set("workflow_slug", workflowSlug);
    return apiFetch(`/marketplace/history?${params}`);
  },

  /** Save a completed workflow run to the approval inbox */
  async saveToInbox(runId: string): Promise<{ deliverable_id: string; already_saved: boolean }> {
    return apiFetch(`/marketplace/runs/${runId}/save-to-inbox`, { method: "POST" });
  },
};
