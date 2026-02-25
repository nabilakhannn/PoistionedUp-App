/**
 * Strategist API -- v2 brand strategist chat with options-based interaction.
 */

import { apiFetch } from "./client";

// ── Response Types ────────────────────────────────────────

export interface StratOption {
  id: string;
  label: string;
  text: string;
}

export interface OptionsResponse {
  type: "options";
  module: string;
  field: string;
  message: string;
  options: StratOption[];
  allow_custom: boolean;
  allow_skip: boolean;
}

export interface RefinementResponse {
  type: "refinement";
  module: string;
  field: string;
  message: string;
  refined_text: string;
  actions: ("confirm" | "edit")[];
}

export interface CompletenessInfo {
  module_name: string;
  module_percent: number;
  overall_percent: number;
}

export interface SaveResponse {
  type: "save";
  module: string;
  field: string;
  value: any;
  message: string;
  completeness?: CompletenessInfo;
}

export interface MessageResponse {
  type: "message";
  message: string;
}

export interface ContentResponse {
  type: "content";
  content_type: string;
  platform: string;
  pillar: string;
  hook: string;
  body: string;
  cta: string;
  message: string;
}

export type StrategistResponseItem =
  | OptionsResponse
  | RefinementResponse
  | SaveResponse
  | MessageResponse
  | ContentResponse;

// ── Completeness Types ────────────────────────────────────

export interface ModuleCompleteness {
  label: string;
  percent: number;
  filled: number;
  total: number;
  filled_fields: string[];
  unfilled_fields: string[];
}

export interface FieldCompleteness {
  overall_percent: number;
  overall_filled: number;
  overall_total: number;
  modules: Record<string, ModuleCompleteness>;
  filled_fields: string[];
  unfilled_fields: string[];
}

// ── Chat Types ────────────────────────────────────────────

export interface StrategistChatRequest {
  brand_id: string;
  message: string;
  file_context?: string;
  file_name?: string;
  attachment_type?: "file" | "link" | "knowledge" | "inspo";
}

export interface StrategistChatResponse {
  responses: StrategistResponseItem[];
  completeness: FieldCompleteness;
  chat_id: string;
  history?: { role: string; content: string }[];
}

export interface NextFieldInfo {
  module?: string;
  field?: string;
  label?: string;
  question?: string;
  all_complete: boolean;
}

// ── API Methods ──────────────────────────────────────────

export const strategistApi = {
  /**
   * Send a message to the brand strategist.
   */
  chat: (data: StrategistChatRequest) =>
    apiFetch<StrategistChatResponse>("/brand/strategist/chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * Get detailed field-level completeness for a brand.
   */
  getCompleteness: (brandId: string) =>
    apiFetch<FieldCompleteness>(
      `/brand/strategist/completeness/${brandId}`
    ),

  /**
   * Get the next recommended field to fill.
   */
  getNextField: (brandId: string) =>
    apiFetch<NextFieldInfo>(
      `/brand/strategist/next-field/${brandId}`
    ),

  /**
   * Resume an existing strategist chat (context-aware greeting + next question).
   */
  resume: (brandId: string) =>
    apiFetch<StrategistChatResponse>(
      `/brand/strategist/chat/${brandId}/resume`,
      { method: "POST" }
    ),

  /**
   * Start a fresh strategist chat (marks old ones as inactive).
   */
  startNew: (brandId: string) =>
    apiFetch<StrategistChatResponse>(
      `/brand/strategist/chat/${brandId}/new`,
      { method: "POST" }
    ),
};
