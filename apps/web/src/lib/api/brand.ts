/**
 * Brand API -- profile, chat, completeness, and suggestions.
 */

import { createClient } from "@/lib/supabase/client";
import { apiFetch, API_BASE } from "./client";

// ── Types ────────────────────────────────────────────────

export interface BrandProfile {
  foundation: Record<string, any>;
  ica: Record<string, any>;
  offer: Record<string, any>;
  brand: Record<string, any>;
  authority: Record<string, any>;
  messaging: Record<string, any>;
  positioning: Record<string, any>;
  competitors: Record<string, any>;
}

export interface BrandCompleteness {
  foundation_percent: number;
  ica_percent: number;
  offer_percent: number;
  brand_percent: number;
  authority_percent: number;
  messaging_percent: number;
  positioning_percent: number;
  competitors_percent: number;
  overall_percent: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  extracted_so_far: Record<string, any>;
  progress: number;
  chat_id: string;
}

export interface ChatHistory {
  chat_id: string | null;
  module: string;
  messages: ChatMessage[];
  extracted: Record<string, any>;
  status: string;
}

export interface ChatSummary {
  chat_id: string;
  module: string;
  title: string | null;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatListResponse {
  module: string;
  chats: ChatSummary[];
}

// ── API Methods ──────────────────────────────────────────

export const brandApi = {
  getProfile: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<BrandProfile>(`/brand${qs}`);
  },

  getCompleteness: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<BrandCompleteness>(`/brand/completeness${qs}`);
  },

  updateFoundation: (data: Record<string, any>, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<{ message: string; foundation: Record<string, any> }>(
      `/brand/foundation${qs}`,
      { method: "PATCH", body: JSON.stringify(data) }
    );
  },

  updateICA: (data: Record<string, any>, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<{ message: string; ica: Record<string, any> }>(
      `/brand/ica${qs}`,
      { method: "PATCH", body: JSON.stringify(data) }
    );
  },

  updateOffer: (data: Record<string, any>, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<{ message: string; offer: Record<string, any> }>(
      `/brand/offer${qs}`,
      { method: "PATCH", body: JSON.stringify(data) }
    );
  },

  updateStatement: (data: Record<string, any>, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<{ message: string; brand: Record<string, any> }>(
      `/brand/statement${qs}`,
      { method: "PATCH", body: JSON.stringify(data) }
    );
  },

  sendChat: (
    module: string,
    message: string,
    fileContext?: string,
    fileName?: string,
    brandId?: string,
    attachmentType?: "file" | "link" | "knowledge" | "inspo"
  ) =>
    apiFetch<ChatResponse>("/brand/chat", {
      method: "POST",
      body: JSON.stringify({
        module,
        message,
        ...(fileContext
          ? {
              file_context: fileContext,
              file_name: fileName,
              ...(attachmentType ? { attachment_type: attachmentType } : {}),
            }
          : {}),
        ...(brandId ? { brand_id: brandId } : {}),
      }),
    }),

  uploadChatFile: async (
    file: File
  ): Promise<{
    filename: string;
    chars_extracted: number;
    truncated: boolean;
    text: string;
    source_type: string;
  }> => {
    let token = "";
    if (typeof window !== "undefined") {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      token = data.session?.access_token ?? "";
    }
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/brand/chat/upload-context`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(body.detail || `Upload failed (${res.status})`);
    }
    return res.json();
  },

  extractLink: (url: string) =>
    apiFetch<{
      url: string;
      platform: string;
      source_type: string;
      chars_extracted: number;
      truncated: boolean;
      text: string;
      metadata: Record<string, any>;
    }>("/brand/chat/extract-link", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  getChatHistory: (module: string, chatId?: string, brandId?: string) => {
    const params = new URLSearchParams();
    if (chatId) params.set("chat_id", chatId);
    if (brandId) params.set("brand_id", brandId);
    const qs = params.toString();
    return apiFetch<ChatHistory>(
      `/brand/chat/${module}${qs ? `?${qs}` : ""}`
    );
  },

  listChats: (module: string, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<ChatListResponse>(`/brand/chats/${module}${qs}`);
  },

  startNewChat: (module: string, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<ChatHistory>(`/brand/chat/${module}/new${qs}`, {
      method: "POST",
    });
  },

  deleteChat: (chatId: string) =>
    apiFetch<{ message: string }>(`/brand/chat/${chatId}`, {
      method: "DELETE",
    }),

  renameChat: (chatId: string, title: string) =>
    apiFetch<{ message: string; title: string }>(
      `/brand/chat/${chatId}/title`,
      { method: "PATCH", body: JSON.stringify({ title }) }
    ),

  completeChat: (module: string, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<{ message: string; merged_fields: number }>(
      `/brand/chat/${module}/complete${qs}`,
      { method: "POST" }
    );
  },

  suggest: (field: string, context?: Record<string, any>) =>
    apiFetch<{ field: string; suggestion: string }>("/brand/suggest", {
      method: "POST",
      body: JSON.stringify({ field, context: context || {} }),
    }),
};

// ── Personal Brands API ──────────────────────────────────

export interface PersonalBrandCreate {
  name: string;
  description?: string;
  model_tier?: string;
}

export interface PersonalBrandUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  model_tier?: string;
}

export interface PersonalBrandSummary {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  model_tier: string;
  completeness: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export interface PersonalBrandDetail extends PersonalBrandSummary {
  profile_json: Record<string, any>;
}

export interface PersonalBrandListResponse {
  brands: PersonalBrandSummary[];
  total: number;
}

export interface ModelTierInfo {
  key: string;
  label: string;
  description: string;
  creative_model: string;
  review_model: string;
  provider: string;
  est_cost_per_workflow: string;
  est_cost_per_chat_msg: string;
}

export interface ModelTierListResponse {
  tiers: ModelTierInfo[];
  current_tier: string;
}

export const personalBrandsApi = {
  list: () => apiFetch<PersonalBrandListResponse>("/brands"),

  get: (brandId: string) =>
    apiFetch<PersonalBrandDetail>(`/brands/${brandId}`),

  create: (data: PersonalBrandCreate) =>
    apiFetch<PersonalBrandDetail>("/brands", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (brandId: string, data: PersonalBrandUpdate) =>
    apiFetch<PersonalBrandDetail>(`/brands/${brandId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (brandId: string) =>
    apiFetch<{ message: string }>(`/brands/${brandId}`, {
      method: "DELETE",
    }),

  updateFoundation: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; foundation: Record<string, any> }>(
      `/brands/${brandId}/foundation`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updateICA: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; ica: Record<string, any> }>(
      `/brands/${brandId}/ica`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updateOffer: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; offer: Record<string, any> }>(
      `/brands/${brandId}/offer`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updateStatement: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; brand: Record<string, any> }>(
      `/brands/${brandId}/statement`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updateAuthority: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; authority: Record<string, any> }>(
      `/brands/${brandId}/authority`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updateMessaging: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; messaging: Record<string, any> }>(
      `/brands/${brandId}/messaging`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updatePositioning: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; positioning: Record<string, any> }>(
      `/brands/${brandId}/positioning`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updateCompetitors: (brandId: string, data: Record<string, any>) =>
    apiFetch<{ message: string; competitors: Record<string, any> }>(
      `/brands/${brandId}/competitors`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  getCompleteness: (brandId: string) =>
    apiFetch<BrandCompleteness>(`/brands/${brandId}/completeness`),

  getModelTiers: (brandId?: string) =>
    apiFetch<ModelTierListResponse>(
      `/brands/model-tiers${brandId ? `?brand_id=${brandId}` : ""}`
    ),

  updateModelTier: (brandId: string, tier: string) =>
    apiFetch<PersonalBrandDetail>(`/brands/${brandId}`, {
      method: "PATCH",
      body: JSON.stringify({ model_tier: tier }),
    }),

  // ── Brand Research Pipeline ──────────────────────────────

  startResearch: (brandId: string, data: { industry: string; name?: string; description?: string; target_audience?: string }) =>
    apiFetch<BrandResearchSession>(`/brands/${brandId}/research`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listResearch: (brandId: string) =>
    apiFetch<{ sessions: BrandResearchSession[]; stages: string[]; stage_labels: Record<string, string> }>(
      `/brands/${brandId}/research`
    ),

  getResearch: (brandId: string, sessionId: string) =>
    apiFetch<BrandResearchSession>(`/brands/${brandId}/research/${sessionId}`),

  runResearchStage: (brandId: string, sessionId: string, runAll: boolean = false) =>
    apiFetch<BrandResearchSession>(
      `/brands/${brandId}/research/${sessionId}/run${runAll ? "?run_all=true" : ""}`,
      { method: "POST" }
    ),

  applyResearch: (brandId: string, sessionId: string) =>
    apiFetch<{ message: string; prefilled_fields: Record<string, string> }>(
      `/brands/${brandId}/research/${sessionId}/apply`,
      { method: "POST" }
    ),

  skipResearchStage: (brandId: string, sessionId: string) =>
    apiFetch<BrandResearchSession>(
      `/brands/${brandId}/research/${sessionId}/skip`,
      { method: "POST" }
    ),
};

// ── Research Types ──────────────────────────────────────────

export interface BrandResearchSession {
  id: string;
  user_id: string;
  brand_id: string;
  seed_input: { name: string; industry: string; description: string; target_audience?: string };
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  current_stage: string;
  stages_completed: string[];
  results: Record<string, any>;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  stages?: string[];
  stage_labels?: Record<string, string>;
}
