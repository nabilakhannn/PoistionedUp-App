/**
 * Gateway API client — OpenClaw gateway health, status, and messaging.
 */
import { apiFetch } from "./client";

// ── Types ─────────────────────────────────────────────────

export interface GatewayHealth {
  connected: boolean;
  status: "healthy" | "unhealthy" | "unreachable" | "timeout" | "error" | "not_configured";
  latency_ms?: number;
  gateway_url?: string;
  version?: string;
  uptime?: string;
  agents_loaded?: number;
  http_status?: number;
  error?: string;
  checked_at?: string;
  mock_mode?: boolean;
}

export interface GatewayAgent {
  id: string;
  name: string;
  status: string;
  model: string | null;
  workspace?: string;
  channels: string[];
  is_default: boolean;
}

export interface GatewaySession {
  id: string;
  agent_id: string | null;
  status: string;
  created_at: string | null;
  last_activity: string | null;
  message_count: number | null;
}

export interface ChecklistItem {
  id: string;
  label: string;
  status: "pass" | "fail" | "warn" | "skip";
  detail: string;
}

export interface GatewayStatus {
  health: GatewayHealth;
  agents: GatewayAgent[];
  sessions: GatewaySession[];
  checklist: ChecklistItem[];
  mock_mode?: boolean;
  config: {
    gateway_url_set: boolean;
    gateway_token_set: boolean;
    agent_api_key_set: boolean;
    openai_key_set: boolean;
  };
}

export interface GatewayMessageResponse {
  session_id?: string;
  response?: string;
  status?: string;
  [key: string]: unknown;
}

// ── API Methods ───────────────────────────────────────────

export const gatewayApi = {
  /** Check gateway connectivity. */
  health: () => apiFetch<GatewayHealth>("/gateway/health"),

  /** Full deployment status (health + agents + sessions + checklist). */
  status: () => apiFetch<GatewayStatus>("/gateway/status"),

  /** List agents from gateway. */
  agents: () => apiFetch<GatewayAgent[]>("/gateway/agents"),

  /** List active sessions on gateway. */
  sessions: () => apiFetch<GatewaySession[]>("/gateway/sessions"),

  /** Send a message to an agent via gateway. */
  sendMessage: (agentId: string, message: string, sessionId?: string) =>
    apiFetch<GatewayMessageResponse>("/gateway/message", {
      method: "POST",
      body: JSON.stringify({
        agent_id: agentId,
        message,
        session_id: sessionId,
      }),
    }),
};
