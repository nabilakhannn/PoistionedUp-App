/**
 * API client for PositionedUp backend.
 *
 * All endpoints require authentication. The token comes from
 * Supabase Auth (cookie-based session via @supabase/ssr).
 */

import { createClient } from "@/lib/supabase/client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let token = "";
  if (typeof window !== "undefined") {
    const supabase = createClient();

    // getSession() triggers token refresh if expired
    const { data, error } = await supabase.auth.getSession();

    if (error) {
      console.error("[apiFetch] Session error:", error);
      window.location.href = "/login";
      throw new Error("Session error");
    }

    token = data.session?.access_token ?? "";

    // No session — redirect to login
    if (!token) {
      console.warn("[apiFetch] No token, redirecting to /login");
      window.location.href = "/login";
      throw new Error("Not authenticated");
    }

    // Check if token is about to expire (within 5 minutes)
    const expiresAt = data.session?.expires_at;
    if (expiresAt && expiresAt < Date.now() / 1000 + 300) {
      console.log("[apiFetch] Token expiring soon, refreshing...");
      const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
      if (refreshError) {
        console.error("[apiFetch] Refresh failed:", refreshError);
        await supabase.auth.signOut();
        window.location.href = "/login";
        throw new Error("Session expired");
      }
      token = refreshData.session?.access_token ?? token;
    }
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });
  } catch (err) {
    console.error("[apiFetch] Network error:", err);
    throw new Error(`Cannot reach the server. Is the backend running on port 8000?`);
  }

  if (res.status === 401) {
    // Token expired or invalid — sign out and redirect
    console.warn("[apiFetch] 401 Unauthorized, signing out");
    if (typeof window !== "undefined") {
      const supabase = createClient();
      await supabase.auth.signOut();
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please sign in again.");
  }

  if (!res.ok) {
    const body = await res.text();
    console.error(`[apiFetch] API error ${res.status}:`, body);
    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json();
}

// ── Brand API ─────────────────────────────────────────────

export interface BrandProfile {
  foundation: Record<string, any>;
  ica: Record<string, any>;
  offer: Record<string, any>;
  brand: Record<string, any>;
}

export interface BrandCompleteness {
  foundation_percent: number;
  ica_percent: number;
  offer_percent: number;
  brand_percent: number;
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

export const brandApi = {
  getProfile: () => apiFetch<BrandProfile>("/brand"),

  getCompleteness: () => apiFetch<BrandCompleteness>("/brand/completeness"),

  updateFoundation: (data: Record<string, any>) =>
    apiFetch<{ message: string; foundation: Record<string, any> }>(
      "/brand/foundation",
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  updateICA: (data: Record<string, any>) =>
    apiFetch<{ message: string; ica: Record<string, any> }>("/brand/ica", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  updateOffer: (data: Record<string, any>) =>
    apiFetch<{ message: string; offer: Record<string, any> }>("/brand/offer", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  updateStatement: (data: Record<string, any>) =>
    apiFetch<{ message: string; brand: Record<string, any> }>(
      "/brand/statement",
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  sendChat: (
    module: string,
    message: string,
    fileContext?: string,
    fileName?: string
  ) =>
    apiFetch<ChatResponse>("/brand/chat", {
      method: "POST",
      body: JSON.stringify({
        module,
        message,
        ...(fileContext ? { file_context: fileContext, file_name: fileName } : {}),
      }),
    }),

  uploadChatFile: async (file: File): Promise<{
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

  getChatHistory: (module: string, chatId?: string) =>
    apiFetch<ChatHistory>(
      `/brand/chat/${module}${chatId ? `?chat_id=${chatId}` : ""}`
    ),

  listChats: (module: string) =>
    apiFetch<ChatListResponse>(`/brand/chats/${module}`),

  startNewChat: (module: string) =>
    apiFetch<ChatHistory>(`/brand/chat/${module}/new`, { method: "POST" }),

  deleteChat: (chatId: string) =>
    apiFetch<{ message: string }>(`/brand/chat/${chatId}`, {
      method: "DELETE",
    }),

  renameChat: (chatId: string, title: string) =>
    apiFetch<{ message: string; title: string }>(
      `/brand/chat/${chatId}/title`,
      { method: "PATCH", body: JSON.stringify({ title }) }
    ),

  completeChat: (module: string) =>
    apiFetch<{ message: string; merged_fields: number }>(
      `/brand/chat/${module}/complete`,
      { method: "POST" }
    ),

  suggest: (field: string, context?: Record<string, any>) =>
    apiFetch<{ field: string; suggestion: string }>("/brand/suggest", {
      method: "POST",
      body: JSON.stringify({ field, context: context || {} }),
    }),
};

// ── Collections API ──────────────────────────────────────

export interface VoiceDNA {
  tone: string;
  sentence_style: string;
  vocabulary_level: string;
  hook_patterns: string[];
  cta_patterns: string[];
  signature_phrases: string[];
  content_structure: string;
  personality_traits: string[];
  sample_hooks: string[];
  analysis_chunk_count: number;
}

export interface CollectionSummary {
  id: string;
  name: string;
  description: string;
  creator_url: string | null;
  resource_count: number;
  voice_dna_ready: boolean;
  created_at: string;
  updated_at: string;
}

export interface CollectionResource {
  id: string;
  type: string;
  title: string;
  source_url: string | null;
  chunk_count: number;
  created_at: string;
}

export interface CollectionDetail {
  id: string;
  name: string;
  description: string;
  creator_url: string | null;
  voice_dna: VoiceDNA;
  resources: CollectionResource[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CollectionSearchResult {
  chunk_text: string;
  resource_title: string;
  similarity: number;
  metadata: Record<string, any>;
}

export const collectionsApi = {
  list: () => apiFetch<CollectionSummary[]>("/collections"),

  get: (id: string) => apiFetch<CollectionDetail>(`/collections/${id}`),

  create: (data: { name: string; description?: string; creator_url?: string }) =>
    apiFetch<CollectionSummary>("/collections", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: { name?: string; description?: string; creator_url?: string }) =>
    apiFetch<CollectionSummary>(`/collections/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/collections/${id}`, { method: "DELETE" }),

  addResources: (id: string, resourceIds: string[]) =>
    apiFetch<{ message: string; updated: number }>(`/collections/${id}/resources`, {
      method: "POST",
      body: JSON.stringify({ resource_ids: resourceIds }),
    }),

  removeResource: (collectionId: string, resourceId: string) =>
    apiFetch<{ message: string }>(`/collections/${collectionId}/resources/${resourceId}`, {
      method: "DELETE",
    }),

  analyzeVoice: (id: string) =>
    apiFetch<{ collection_id: string; collection_name: string; voice_dna: VoiceDNA; message: string }>(
      `/collections/${id}/analyze-voice`,
      { method: "POST" }
    ),

  search: (id: string, query: string, limit?: number) =>
    apiFetch<{ collection_id: string; collection_name: string; query: string; results: CollectionSearchResult[] }>(
      `/collections/${id}/search`,
      { method: "POST", body: JSON.stringify({ query, limit: limit || 5 }) }
    ),
};

// ── Performance API ──────────────────────────────────────

export interface ContentPostSummary {
  id: string;
  title: string;
  content_type: string;
  platform: string;
  hook_type: string | null;
  topic: string | null;
  topic_category: string | null;
  performance_tier: string | null;
  engagement_rate: number | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  published_at: string | null;
  created_at: string;
}

export interface ContentPostDetail extends ContentPostSummary {
  hook_used: string | null;
  content_body: string | null;
  workflow_id: string | null;
  collection_id: string | null;
  published_url: string | null;
  day_of_week: string | null;
  shares: number | null;
  saves: number | null;
  watch_time_seconds: number | null;
  click_through_rate: number | null;
  impressions: number | null;
  reach: number | null;
  subscribers_gained: number | null;
  agent_analysis: Record<string, any>;
  tags: string[];
  metadata: Record<string, any>;
  updated_at: string;
}

export interface PlatformBreakdown {
  platform: string;
  post_count: number;
  avg_engagement_rate: number | null;
  avg_views: number | null;
  top_tier_count: number;
}

export interface TopicBreakdown {
  topic_category: string;
  post_count: number;
  avg_engagement_rate: number | null;
  avg_views: number | null;
}

export interface HookBreakdown {
  hook_type: string;
  post_count: number;
  avg_engagement_rate: number | null;
  example_hooks: string[];
}

export interface PatternDetected {
  pattern: string;
  evidence: string;
  confidence: number;
}

export interface PerformanceAnalytics {
  total_posts: number;
  platforms: PlatformBreakdown[];
  top_topics: TopicBreakdown[];
  top_hook_types: HookBreakdown[];
  best_day_of_week: string | null;
  patterns: PatternDetected[];
  top_hooks: string[];
  anti_hooks: string[];
}

export const performanceApi = {
  list: (platform?: string, tier?: string) => {
    const params = new URLSearchParams();
    if (platform) params.set("platform", platform);
    if (tier) params.set("tier", tier);
    const qs = params.toString();
    return apiFetch<ContentPostSummary[]>(`/content-posts${qs ? `?${qs}` : ""}`);
  },

  get: (id: string) => apiFetch<ContentPostDetail>(`/content-posts/${id}`),

  create: (data: {
    title: string;
    content_type: string;
    platform: string;
    hook_used?: string;
    hook_type?: string;
    topic?: string;
    topic_category?: string;
    content_body?: string;
    published_url?: string;
    published_at?: string;
    day_of_week?: string;
    tags?: string[];
  }) =>
    apiFetch<ContentPostSummary>("/content-posts", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateMetrics: (id: string, data: {
    views?: number;
    likes?: number;
    comments?: number;
    shares?: number;
    saves?: number;
    watch_time_seconds?: number;
    click_through_rate?: number;
    impressions?: number;
    reach?: number;
    subscribers_gained?: number;
  }) =>
    apiFetch<ContentPostDetail>(`/content-posts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  analytics: () => apiFetch<PerformanceAnalytics>("/content-posts/analytics"),

  analyze: (id: string) =>
    apiFetch<{ post_id: string; performance_tier: string | null; analysis: Record<string, any>; message: string }>(
      `/content-posts/${id}/analyze`,
      { method: "POST" }
    ),
};

// ── Agent Memory API ────────────────────────────────────

export interface AgentMemorySummary {
  id: string;
  memory_type: string;
  content: string;
  confidence: number;
  status: string;
  platform: string | null;
  category: string | null;
  source: string | null;
  last_used_at: string | null;
  created_at: string;
}

export interface AgentMemoryDetail extends AgentMemorySummary {
  evidence: any[];
  related_post_ids: string[];
  supersedes_id: string | null;
  updated_at: string;
}

export interface MemorySynthesisResponse {
  new_memories_created: number;
  memories_superseded: number;
  patterns_detected: string[];
  message: string;
}

export const memoryApi = {
  list: (memoryType?: string, status?: string, platform?: string) => {
    const params = new URLSearchParams();
    if (memoryType) params.set("memory_type", memoryType);
    if (status) params.set("status", status);
    if (platform) params.set("platform", platform);
    const qs = params.toString();
    return apiFetch<AgentMemorySummary[]>(`/memory${qs ? `?${qs}` : ""}`);
  },

  pending: () => apiFetch<AgentMemorySummary[]>("/memory/pending"),

  get: (id: string) => apiFetch<AgentMemoryDetail>(`/memory/${id}`),

  create: (data: {
    memory_type: string;
    content: string;
    confidence?: number;
    platform?: string;
    category?: string;
    source?: string;
  }) =>
    apiFetch<AgentMemorySummary>("/memory", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: {
    content?: string;
    confidence?: number;
    platform?: string;
    category?: string;
  }) =>
    apiFetch<AgentMemorySummary>(`/memory/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  approve: (id: string, action: "approve" | "dismiss" = "approve", editedContent?: string) =>
    apiFetch<AgentMemorySummary>(`/memory/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ action, edited_content: editedContent }),
    }),

  synthesize: () =>
    apiFetch<MemorySynthesisResponse>("/memory/synthesize", {
      method: "POST",
    }),

  delete: (id: string) =>
    apiFetch<void>(`/memory/${id}`, { method: "DELETE" }),
};

// ── Experiments API ─────────────────────────────────────

export interface ExperimentSummary {
  id: string;
  hypothesis: string;
  variable: string;
  variant_a: string;
  variant_b: string;
  platform: string;
  status: string;
  target_posts: number;
  variant_a_count: number;
  variant_b_count: number;
  variant_a_avg_engagement: number | null;
  variant_b_avg_engagement: number | null;
  winner: string | null;
  conclusion: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ExperimentDetail extends ExperimentSummary {
  variant_a_posts: string[];
  variant_b_posts: string[];
  resulting_memory_id: string | null;
  updated_at: string;
}

export interface ExperimentActionResponse {
  id: string;
  status: string;
  message: string;
}

export interface SelfVoiceDNA {
  tone: string;
  sentence_style: string;
  vocabulary_level: string;
  avg_sentence_length: number | null;
  hook_patterns: string[];
  cta_patterns: string[];
  signature_phrases: string[];
  content_structure: string;
  personality_traits: string[];
  sample_hooks: string[];
  posts_analyzed: number;
}

export interface VoiceDriftResult {
  drift_score: number;
  drift_level: string;
  details: string[];
  recommendation: string;
  baseline_available: boolean;
}

export const experimentsApi = {
  list: (status?: string, platform?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (platform) params.set("platform", platform);
    const qs = params.toString();
    return apiFetch<ExperimentSummary[]>(`/experiments${qs ? `?${qs}` : ""}`);
  },

  get: (id: string) => apiFetch<ExperimentDetail>(`/experiments/${id}`),

  create: (data: {
    hypothesis: string;
    variable: string;
    variant_a: string;
    variant_b: string;
    platform: string;
    target_posts?: number;
  }) =>
    apiFetch<ExperimentSummary>("/experiments", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: { hypothesis?: string; target_posts?: number }) =>
    apiFetch<ExperimentSummary>(`/experiments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  approve: (id: string) =>
    apiFetch<ExperimentActionResponse>(`/experiments/${id}/approve`, {
      method: "POST",
    }),

  cancel: (id: string) =>
    apiFetch<ExperimentActionResponse>(`/experiments/${id}/cancel`, {
      method: "POST",
    }),

  assign: (id: string, postId: string, variant: "variant_a" | "variant_b") =>
    apiFetch<ExperimentActionResponse>(`/experiments/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ post_id: postId, variant }),
    }),

  conclude: (id: string) =>
    apiFetch<ExperimentDetail>(`/experiments/${id}/conclude`, {
      method: "POST",
    }),

  autoPropose: () =>
    apiFetch<ExperimentSummary[]>("/experiments/auto-propose", {
      method: "POST",
    }),

  delete: (id: string) =>
    apiFetch<void>(`/experiments/${id}`, { method: "DELETE" }),
};

// ── Self-Voice API ──────────────────────────────────────

export const voiceApi = {
  analyzeSelf: () =>
    apiFetch<{ voice_dna: SelfVoiceDNA; message: string }>("/voice/analyze-self", {
      method: "POST",
    }),

  getBaseline: () => apiFetch<SelfVoiceDNA | null>("/voice/baseline"),

  checkDrift: (text: string) =>
    apiFetch<VoiceDriftResult>("/voice/drift-check", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
};

// ── Content / Workflow API ────────────────────────────

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

export interface ContentAsset {
  id: string;
  workflow_id: string;
  asset_type: string;
  platform: string | null;
  title: string | null;
  body: Record<string, any> | null;
  version: number;
  is_latest: boolean;
  status: string;
  feedback: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeResponse {
  id: string;
  status: string;
  message: string;
}

export const contentApi = {
  /** List all workflows for the current user */
  list: () => apiFetch<WorkflowSummary[]>("/workflows"),

  /** Get workflow detail */
  get: (id: string) => apiFetch<WorkflowDetail>(`/workflows/${id}`),

  /** Create a new content workflow */
  create: (data: {
    goal_text: string;
    platforms: string[];
    settings?: Record<string, any>;
  }) =>
    apiFetch<WorkflowCreated>("/workflows", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Get content assets for a workflow */
  getAssets: (workflowId: string) =>
    apiFetch<ContentAsset[]>(`/workflows/${workflowId}/assets`),

  /** Select a topic to resume the pipeline */
  selectTopic: (workflowId: string, topicId: string) =>
    apiFetch<ResumeResponse>(`/workflows/${workflowId}/topic`, {
      method: "POST",
      body: JSON.stringify({ selected_topic_id: topicId }),
    }),

  /** Select a hook to resume the pipeline */
  selectHook: (workflowId: string, hookId: string) =>
    apiFetch<ResumeResponse>(`/workflows/${workflowId}/hook`, {
      method: "POST",
      body: JSON.stringify({ selected_hook_id: hookId }),
    }),

  /** Approve or reject a workflow */
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

  /** Abandon a workflow */
  abandon: (workflowId: string) =>
    apiFetch<ResumeResponse>(`/workflows/${workflowId}/abandon`, {
      method: "POST",
    }),

  /** Update a content asset (creates a new version, preserves old) */
  updateAsset: (workflowId: string, assetId: string, body: Record<string, any>) =>
    apiFetch<ContentAsset>(`/workflows/${workflowId}/assets/${assetId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  /** Get all versions of a content asset */
  getAssetVersions: (workflowId: string, assetId: string) =>
    apiFetch<ContentAsset[]>(`/workflows/${workflowId}/assets/${assetId}/versions`),

  /** Restore an older version of an asset */
  restoreAssetVersion: (workflowId: string, assetId: string) =>
    apiFetch<ContentAsset>(`/workflows/${workflowId}/assets/${assetId}/restore`, {
      method: "POST",
    }),

  /** Fetch topic candidates */
  getTopics: (workflowId: string) =>
    apiFetch<{ topics: any[] }>(`/workflows/${workflowId}/topics`),

  /** Fetch hook candidates */
  getHooks: (workflowId: string) =>
    apiFetch<{ hooks: any[]; selected_topic: any }>(`/workflows/${workflowId}/hooks`),

  /** Export content to clipboard (plain text) */
  exportClipboard: (workflowId: string) =>
    apiFetch<{ text: string; format: string }>(`/workflows/${workflowId}/export/clipboard`, {
      method: "POST",
    }),

  /** Export content to Google Docs (requires Google OAuth) */
  exportGoogleDocs: (workflowId: string) =>
    apiFetch<{ url: string; format: string }>(`/workflows/${workflowId}/export/google-docs`, {
      method: "POST",
    }),

  /** Export content to Notion (requires Notion OAuth) */
  exportNotion: (workflowId: string) =>
    apiFetch<{ url: string; format: string }>(`/workflows/${workflowId}/export/notion`, {
      method: "POST",
    }),

  /** Export content as markdown (returns raw text) */
  exportMarkdown: async (workflowId: string): Promise<string> => {
    if (typeof window === "undefined") throw new Error("Client only");
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token ?? "";
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/export/markdown`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
    if (!res.ok) throw new Error("Export failed");
    return res.text();
  },
};

// ── OAuth / Connections API ──────────────────────────

export interface OAuthStatus {
  connected: boolean;
  provider: string;
  scopes?: string[];
  email?: string;
}

export interface OAuthAuthURL {
  url: string;
  provider: string;
}

export const oauthApi = {
  /** Get Google OAuth consent URL */
  googleAuthUrl: () => apiFetch<OAuthAuthURL>("/oauth/google/auth-url"),

  /** Exchange Google auth code for tokens */
  googleCallback: (code: string) =>
    apiFetch<{ message: string; provider: string }>("/oauth/google/callback", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  /** Check Google connection status */
  googleStatus: () => apiFetch<OAuthStatus>("/oauth/google/status"),

  /** Disconnect Google */
  googleDisconnect: () =>
    apiFetch<{ message: string; provider: string }>("/oauth/google/disconnect", {
      method: "DELETE",
    }),

  /** Get Notion OAuth consent URL */
  notionAuthUrl: () => apiFetch<OAuthAuthURL>("/oauth/notion/auth-url"),

  /** Exchange Notion auth code for tokens */
  notionCallback: (code: string) =>
    apiFetch<{ message: string; provider: string; workspace_name?: string }>(
      "/oauth/notion/callback",
      {
        method: "POST",
        body: JSON.stringify({ code }),
      }
    ),

  /** Check Notion connection status */
  notionStatus: () => apiFetch<OAuthStatus>("/oauth/notion/status"),

  /** Disconnect Notion */
  notionDisconnect: () =>
    apiFetch<{ message: string; provider: string }>("/oauth/notion/disconnect", {
      method: "DELETE",
    }),
};

// ── Schedule API ─────────────────────────────────────

export interface ScheduledItem {
  id: string;
  user_id: string;
  title: string;
  platform: string;
  content_type: string;
  body_preview: string | null;
  content_json: Record<string, any>;
  workflow_id: string | null;
  asset_id: string | null;
  content_post_id: string | null;
  status: "draft" | "scheduled" | "published" | "archived";
  column_order: number;
  scheduled_at: string | null;
  published_at: string | null;
  published_url: string | null;
  color_label: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface KanbanBoard {
  draft: ScheduledItem[];
  scheduled: ScheduledItem[];
  published: ScheduledItem[];
  archived: ScheduledItem[];
}

export interface ImportResult {
  imported: number;
  items: ScheduledItem[];
  message: string;
}

export const scheduleApi = {
  /** Get the full kanban board (items grouped by status) */
  getBoard: () => apiFetch<KanbanBoard>("/schedule"),

  /** Get items within a date range for the calendar view */
  getCalendar: (start: string, end: string) =>
    apiFetch<ScheduledItem[]>(
      `/schedule/calendar?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
    ),

  /** Create a new scheduled item */
  create: (data: {
    title: string;
    platform?: string;
    content_type?: string;
    body_preview?: string;
    content_json?: Record<string, any>;
    status?: string;
    scheduled_at?: string;
    color_label?: string;
    notes?: string;
    workflow_id?: string;
    asset_id?: string;
  }) =>
    apiFetch<ScheduledItem>("/schedule", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Import approved content from a workflow */
  importFromWorkflow: (workflowId: string) =>
    apiFetch<ImportResult>(`/schedule/import/${workflowId}`, {
      method: "POST",
    }),

  /** Update a scheduled item */
  update: (id: string, data: Partial<ScheduledItem>) =>
    apiFetch<ScheduledItem>(`/schedule/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** Move an item to a different column and position (drag-and-drop) */
  move: (id: string, status: string, columnOrder: number) =>
    apiFetch<ScheduledItem>(`/schedule/${id}/move`, {
      method: "PATCH",
      body: JSON.stringify({ status, column_order: columnOrder }),
    }),

  /** Delete a scheduled item */
  delete: (id: string) =>
    apiFetch<void>(`/schedule/${id}`, { method: "DELETE" }),
};

// ── Research API ──────────────────────────────────────

export interface ResearchResult {
  title: string;
  url: string;
  snippet?: string;
  description?: string;
  publisher?: string;
  views?: string;
  source: string;
}

export interface ResearchResponse {
  web_results: ResearchResult[];
  youtube_trends: ResearchResult[];
  reddit_discussions: ResearchResult[];
  competitor_analysis: Record<string, unknown>[];
  signal_count: number;
  summary: string;
}

export interface QuickSearchResponse {
  results: ResearchResult[];
  source: string;
}

export const researchApi = {
  /** Full multi-source research */
  run: (
    topic: string,
    sources?: { web?: boolean; youtube?: boolean; reddit?: boolean },
    competitorUrls?: string[],
    maxResults?: number
  ) =>
    apiFetch<ResearchResponse>("/research", {
      method: "POST",
      body: JSON.stringify({
        topic,
        sources: sources || { web: true, youtube: true, reddit: true },
        competitor_urls: competitorUrls || [],
        max_results: maxResults || 8,
      }),
    }),

  /** Quick web search */
  quickSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/quick", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 5 }),
    }),

  /** YouTube trend search */
  youtubeSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/youtube", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 5 }),
    }),

  /** Reddit discussion search */
  redditSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/reddit", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 5 }),
    }),
};
