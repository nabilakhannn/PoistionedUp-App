/**
 * Agent Bridge API client - OpenClaw agent endpoints.
 *
 * These endpoints are called server-side by OpenClaw agents using API key auth.
 * The frontend uses them for status display and the Settings page where users
 * can test the agent bridge connectivity and view available endpoints.
 */
import { apiFetch } from "./client";

// ── Types ─────────────────────────────────────────────────

export interface BrandContext {
  brand_id: string;
  brand_name: string;
  completeness_pct: number;
  profile: Record<string, unknown>;
  recent_memories: Array<{
    id: string;
    memory_type: string;
    content: string;
    created_at: string;
  }>;
  performance_summary: {
    total_posts?: number;
    avg_engagement_rate?: number;
    tier_distribution?: Record<string, number>;
    top_posts?: Array<{
      title: string;
      engagement_rate: number;
      platform: string;
    }>;
  };
  voice_dna: Record<string, unknown>;
  active_experiments: Array<{
    id: string;
    hypothesis: string;
    status: string;
    variable: string;
    winner: string | null;
  }>;
  content_pillars: string[];
  writing_rules: string;
}

export interface KnowledgeChunk {
  resource_id: string;
  resource_title: string;
  section: string | null;
  is_gold: boolean;
  chunk_text: string;
  similarity: number;
  tags: string[];
}

export interface KnowledgeSearchResult {
  query: string;
  results: KnowledgeChunk[];
  total_found: number;
}

export interface AgentReportResponse {
  message_id: string | null;
  memory_id: string | null;
  deliverable_id: string | null;
}

export interface PipelineTriggerResponse {
  workflow_id: string;
  status: string;
}

export interface TaskSyncResponse {
  created: number;
  updated: number;
  total: number;
}

export interface BrandSummary {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Agent Bridge API ──────────────────────────────────────

export const agentBridgeApi = {
  /** Get full brand context (profile + memory + performance + voice) */
  getContext: (brandId: string) =>
    apiFetch<BrandContext>(`/agent-api/context/${brandId}`),

  /** Semantic search across knowledge base */
  searchKnowledge: (params: {
    query: string;
    brand_id?: string;
    limit?: number;
    threshold?: number;
    gold_only?: boolean;
  }) =>
    apiFetch<KnowledgeSearchResult>("/agent-api/knowledge/search", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  /** Submit agent report / observation */
  submitReport: (params: {
    agent_id: string;
    task_id?: string;
    brand_id?: string;
    report_type?: string;
    title: string;
    content: string;
    tags?: string[];
    save_to_memory?: boolean;
  }) =>
    apiFetch<AgentReportResponse>("/agent-api/report", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  /** Trigger content pipeline for a brand */
  triggerPipeline: (params: {
    brand_id: string;
    topic?: string;
    objective?: string;
    content_type?: string;
    platforms?: string[];
    tone?: string;
    content_length?: string;
  }) =>
    apiFetch<PipelineTriggerResponse>("/agent-api/pipeline/trigger", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  /** Sync tasks from task_board.md to database */
  syncTasks: (params: {
    agent_id: string;
    tasks: Array<{
      id: string;
      title: string;
      brief?: string;
      priority?: string;
      status?: string;
      assignee_id?: string;
      tags?: string[];
    }>;
  }) =>
    apiFetch<TaskSyncResponse>("/agent-api/tasks/sync", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  /** Send agent heartbeat */
  heartbeat: (params: {
    agent_id: string;
    status: string;
    status_reason?: string;
    current_task_id?: string;
  }) =>
    apiFetch<{ ok: boolean; agent_id: string; recorded_at: string }>("/agent-api/heartbeat", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  /** List all user brands */
  listBrands: () =>
    apiFetch<BrandSummary[]>("/agent-api/brands"),

  /** Search inspo board items */
  searchInspo: (params: {
    board_id?: string;
    brand_id?: string;
    query?: string;
    starred_only?: boolean;
    limit?: number;
  }) =>
    apiFetch("/agent-api/inspo/search", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  /** Get active brand */
  getActiveBrand: () =>
    apiFetch("/agent-api/active-brand"),

  /** Get real agent activity feed from agent_ledger */
  getActivityFeed: (limit?: number) =>
    apiFetch<{
      items: Array<{
        id: string;
        agent_id: string;
        task_type: string;
        summary: string;
        status: string;
        created_at: string;
        brand_id: string | null;
        emoji: string;
      }>;
      total: number;
    }>(`/agent-api/activity-feed?limit=${limit ?? 20}`),

  /** Get real analytics summary from agent_ledger + agent_deliverables */
  getAnalyticsSummary: (brandId?: string) =>
    apiFetch<{
      posts: {
        total_generated: number;
        approved: number;
        rejected: number;
        approval_rate: number;
        avg_qa_score: number;
      };
      agents: {
        tasks_completed: number;
        tasks_failed: number;
        by_agent: Record<string, number>;
      };
      rejection_reasons: Record<string, number>;
    }>(`/agent-api/analytics-summary${brandId ? `?brand_id=${brandId}` : ""}`),

  /** Get proactive Jumbo suggestions based on 7 trigger conditions */
  getProactiveSuggestions: (brandId?: string) =>
    apiFetch<{
      suggestions: Array<{
        id: string;
        priority: "urgent" | "high" | "normal";
        trigger_type: string;
        title: string;
        body: string;
        action_url: string;
        cta: string;
      }>;
      total: number;
    }>(`/agent-api/suggestions${brandId ? `?brand_id=${brandId}` : ""}`),
};
