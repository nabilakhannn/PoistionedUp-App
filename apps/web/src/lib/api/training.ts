/**
 * Agent Training API client.
 *
 * Two scopes:
 *   - adminTrainingApi: Admin endpoints for managing prompt configs, examples, feedback review
 *   - userTrainingApi: User endpoints for submitting feedback and custom instructions
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────────────

export interface PromptConfig {
  id: string;
  config_type: string;
  config_key: string;
  content: string;
  version: number;
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface TrainingExample {
  id: string;
  category: string;
  module: string | null;
  field: string | null;
  user_input: string;
  ideal_response: string;
  context_notes: string | null;
  tags: string[];
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface FeedbackEntry {
  id: string;
  user_id: string;
  brand_id: string | null;
  chat_id: string | null;
  message_index: number | null;
  feedback_type: string;
  feedback_text: string | null;
  original_response: string;
  response_metadata: Record<string, unknown>;
  created_at: string | null;
}

export interface FeedbackSummary {
  total_feedback: number;
  thumbs_up: number;
  thumbs_down: number;
  corrections: number;
  voice_mismatches: number;
  recent_feedback: FeedbackEntry[];
}

export interface CustomInstructions {
  id: string;
  user_id: string;
  brand_id: string | null;
  instructions: string;
  tone_preference: string | null;
  avoid_topics: string[];
  focus_areas: string[];
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface TrainingStats {
  total_configs: number;
  total_examples: number;
  total_feedback: number;
  feedback_by_type: Record<string, number>;
  recent_corrections: FeedbackEntry[];
}

// ── Admin API ────────────────────────────────────────────────────

export const adminTrainingApi = {
  // Prompt Configs
  listConfigs: (configType?: string) => {
    const params = configType ? `?config_type=${configType}` : "";
    return apiFetch<PromptConfig[]>(`/admin/training/config${params}`);
  },

  getConfig: (configKey: string) =>
    apiFetch<PromptConfig>(`/admin/training/config/${configKey}`),

  updateConfig: (configKey: string, content: string, metadata?: Record<string, unknown>) =>
    apiFetch<PromptConfig>(`/admin/training/config/${configKey}`, {
      method: "PUT",
      body: JSON.stringify({ content, metadata }),
    }),

  getConfigHistory: (configKey: string) =>
    apiFetch<PromptConfig[]>(`/admin/training/config/${configKey}/history`),

  // Training Examples
  listExamples: (category?: string, module?: string) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (module) params.set("module", module);
    const qs = params.toString();
    return apiFetch<TrainingExample[]>(`/admin/training/examples${qs ? `?${qs}` : ""}`);
  },

  createExample: (data: {
    category: string;
    module?: string;
    field?: string;
    user_input: string;
    ideal_response: string;
    context_notes?: string;
    tags?: string[];
  }) =>
    apiFetch<TrainingExample>("/admin/training/examples", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateExample: (exampleId: string, data: Partial<TrainingExample>) =>
    apiFetch<TrainingExample>(`/admin/training/examples/${exampleId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteExample: (exampleId: string) =>
    apiFetch<{ status: string; id: string }>(`/admin/training/examples/${exampleId}`, {
      method: "DELETE",
    }),

  // Feedback Review
  listFeedback: (feedbackType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (feedbackType) params.set("feedback_type", feedbackType);
    if (limit) params.set("limit", String(limit));
    const qs = params.toString();
    return apiFetch<FeedbackEntry[]>(`/admin/training/feedback${qs ? `?${qs}` : ""}`);
  },

  // Stats
  getStats: () => apiFetch<TrainingStats>("/admin/training/stats"),
};

// ── User API ─────────────────────────────────────────────────────

export const userTrainingApi = {
  // Feedback
  submitFeedback: (data: {
    brand_id: string;
    chat_id?: string;
    message_index?: number;
    feedback_type: "thumbs_up" | "thumbs_down" | "correction" | "voice_mismatch";
    feedback_text?: string;
    original_response?: string;
    response_metadata?: Record<string, unknown>;
  }) =>
    apiFetch<FeedbackEntry>("/training/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getFeedbackHistory: (brandId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (brandId) params.set("brand_id", brandId);
    if (limit) params.set("limit", String(limit));
    const qs = params.toString();
    return apiFetch<FeedbackEntry[]>(`/training/feedback/history${qs ? `?${qs}` : ""}`);
  },

  getFeedbackSummary: (brandId?: string) => {
    const params = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<FeedbackSummary>(`/training/feedback/summary${params}`);
  },

  // Custom Instructions
  getInstructions: (brandId: string) =>
    apiFetch<CustomInstructions | null>(`/training/instructions/${brandId}`),

  saveInstructions: (brandId: string, data: {
    instructions: string;
    tone_preference?: string;
    avoid_topics?: string[];
    focus_areas?: string[];
  }) =>
    apiFetch<CustomInstructions>(`/training/instructions/${brandId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};
