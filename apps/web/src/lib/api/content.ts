/**
 * Content API -- workflows, content chat, and content assets.
 */

import { createClient } from "@/lib/supabase/client";
import { apiFetch, API_BASE } from "./client";

// ── Workflow Types ───────────────────────────────────────

export interface WorkflowSummary {
  id: string;
  status: string;
  goal_text: string;
  current_step: string | null;
  active_version: number;
  created_at: string;
  updated_at: string;
  platforms: string[];
  estimated_cost: number;
  objective?: string | null;
  content_type?: string | null;
}

export interface WorkflowDetail extends WorkflowSummary {
  settings: Record<string, any>;
  profile_snapshot: Record<string, any>;
  workflow_plan: Record<string, any> | null;
  error_message: string | null;
}

export interface WorkflowCreated {
  id: string;
  status: string;
  message: string;
}

export interface ExecuteResult {
  id: string;
  status: string;
  current_step: string | null;
  error_message: string | null;
}

export interface ContentAsset {
  id: string;
  workflow_id: string;
  type: string;
  platform: string;
  content_json: Record<string, any> | null;
  version: number;
  is_latest: boolean;
  status: string;
  feedback: string | null;
  created_at: string;
  updated_at: string;
}

export interface StepSnapshot {
  id: string;
  step_id: string;
  version: number;
  created_at: string;
  summary: Record<string, any>;
}

export interface ResumeResponse {
  id: string;
  status: string;
  message: string;
}

// ── Workflow API ─────────────────────────────────────────

export const contentApi = {
  list: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<WorkflowSummary[]>(`/workflows${qs}`);
  },

  get: (id: string) => apiFetch<WorkflowDetail>(`/workflows/${id}`),

  create: (data: {
    goal_text: string;
    platforms: string[];
    settings?: Record<string, any>;
    brand_id?: string;
  }) =>
    apiFetch<WorkflowCreated>("/workflows", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * Execute the pipeline inline (no worker needed).
   * Runs until the next interrupt point or completion.
   * This call can take 30-90 seconds depending on the pipeline segment.
   */
  execute: (workflowId: string) =>
    apiFetch<ExecuteResult>(`/workflows/${workflowId}/execute`, {
      method: "POST",
    }),

  getAssets: (workflowId: string) =>
    apiFetch<ContentAsset[]>(`/workflows/${workflowId}/assets`),

  selectTopic: (workflowId: string, topicId: string) =>
    apiFetch<ResumeResponse>(`/workflows/${workflowId}/topic`, {
      method: "POST",
      body: JSON.stringify({ selected_topic_id: topicId }),
    }),

  selectHook: (workflowId: string, hookId: string) =>
    apiFetch<ResumeResponse>(`/workflows/${workflowId}/hook`, {
      method: "POST",
      body: JSON.stringify({ selected_hook_id: hookId }),
    }),

  approve: (
    workflowId: string,
    decision: "approved" | "rejected",
    feedback?: string,
    regenFromStep?: string
  ) =>
    apiFetch<ResumeResponse>(`/workflows/${workflowId}/approve`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        feedback: feedback || "",
        regen_from_step: regenFromStep || "",
      }),
    }),

  abandon: (workflowId: string) =>
    apiFetch<ResumeResponse>(`/workflows/${workflowId}/abandon`, {
      method: "POST",
    }),

  updateAsset: (
    workflowId: string,
    assetId: string,
    body: Record<string, any>
  ) =>
    apiFetch<ContentAsset>(`/workflows/${workflowId}/assets/${assetId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  getAssetVersions: (workflowId: string, assetId: string) =>
    apiFetch<ContentAsset[]>(
      `/workflows/${workflowId}/assets/${assetId}/versions`
    ),

  restoreAssetVersion: (workflowId: string, assetId: string) =>
    apiFetch<ContentAsset>(
      `/workflows/${workflowId}/assets/${assetId}/restore`,
      { method: "POST" }
    ),

  getSnapshots: (workflowId: string) =>
    apiFetch<{ snapshots: StepSnapshot[] }>(
      `/workflows/${workflowId}/snapshots`
    ),

  getTopics: (workflowId: string) =>
    apiFetch<{ topics: any[] }>(`/workflows/${workflowId}/topics`),

  getHooks: (workflowId: string) =>
    apiFetch<{ hooks: any[]; selected_topic: any }>(
      `/workflows/${workflowId}/hooks`
    ),

  exportClipboard: (workflowId: string) =>
    apiFetch<{ text: string; format: string }>(
      `/workflows/${workflowId}/export/clipboard`,
      { method: "POST" }
    ),

  exportGoogleDocs: (workflowId: string) =>
    apiFetch<{ url: string; format: string }>(
      `/workflows/${workflowId}/export/google-docs`,
      { method: "POST" }
    ),

  exportNotion: (workflowId: string) =>
    apiFetch<{ url: string; format: string }>(
      `/workflows/${workflowId}/export/notion`,
      { method: "POST" }
    ),

  exportMarkdown: async (workflowId: string): Promise<string> => {
    if (typeof window === "undefined") throw new Error("Client only");
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token ?? "";
    const res = await fetch(
      `${API_BASE}/workflows/${workflowId}/export/markdown`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    if (!res.ok) throw new Error("Export failed");
    return res.text();
  },
};

// ── Content Chat (Manual Mode) ──────────────────────────

export interface ContentChatMessage {
  role: string;
  content: string;
}

export interface ContentChatResponse {
  reply: string;
  chat_id: string;
  messages: ContentChatMessage[];
}

export interface ContentChatListItem {
  chat_id: string;
  title: string | null;
  preview: string;
  settings: Record<string, any>;
  created_at: string;
  message_count: number;
}

export interface ContentChatHistory {
  chat_id: string;
  messages: ContentChatMessage[];
  settings: Record<string, any>;
  created_at: string;
}

export const contentChatApi = {
  sendMessage: (data: {
    message: string;
    chat_id?: string;
    brand_id?: string;
    settings?: Record<string, any>;
  }) =>
    apiFetch<ContentChatResponse>("/content-chat/message", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listChats: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<ContentChatListItem[]>(`/content-chat/chats${qs}`);
  },

  getChat: (chatId: string) =>
    apiFetch<ContentChatHistory>(`/content-chat/chats/${chatId}`),

  deleteChat: (chatId: string) =>
    apiFetch<any>(`/content-chat/chats/${chatId}`, { method: "DELETE" }),
};
