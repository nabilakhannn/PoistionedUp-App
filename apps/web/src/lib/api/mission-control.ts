/**
 * Mission Control API client - Agent dashboard, tasks, messages, deliverables.
 */
import { apiFetch } from "./client";

// ── Types ─────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  role: string;
  role_type: "lead" | "specialist" | "integrator";
  model_provider: string | null;
  model_name: string | null;
  status: "idle" | "working" | "error" | "paused";
  status_reason: string | null;
  avatar_emoji: string;
  skills: string[];
  about: string | null;
  workspace_path: string | null;
  last_heartbeat_at: string | null;
  created_at: string;
  updated_at: string;
  task_count?: number;
  autonomy_enabled?: boolean;
  confidence_threshold?: number;
  auto_execute?: boolean;
}

export interface AgentTask {
  id: string;
  title: string;
  brief: string | null;
  priority: "P0" | "P1" | "P2" | "P3";
  status: "backlog" | "assigned" | "in_progress" | "review" | "ready" | "done" | "archived";
  assignee_id: string | null;
  tags: string[];
  input_ref: string | null;
  output_ref: string | null;
  notes: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  assignee?: Agent | null;
  deliverable_count?: number;
}

export interface AgentMessage {
  id: string;
  from_agent_id: string | null;
  to_agent_id: string | null;
  message: string;
  message_type: "chat" | "delegation" | "status" | "deliverable" | "escalation" | "broadcast";
  task_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  from_agent?: Agent | null;
  to_agent?: Agent | null;
}

export interface Deliverable {
  id: string;
  task_id: string;
  title: string;
  file_path: string | null;
  content: string | null;
  deliverable_type: "document" | "image" | "code" | "report" | "content";
  created_by_agent_id: string | null;
  status: "draft" | "review" | "approved" | "rejected";
  feedback: string | null;
  qa_score?: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  agents_total: number;
  agents_active: number;
  tasks_total: number;
  tasks_by_status: Record<string, number>;
  tasks_completed_today: number;
  messages_today: number;
  deliverables_pending_review: number;
}

export interface OrchestratorActivity {
  delegations: AgentMessage[];
  recent_tasks_created: AgentTask[];
  sub_agent_statuses: Agent[];
  timeline: AgentMessage[];
}

// ── API Methods ───────────────────────────────────────────

export const missionControlApi = {
  // Dashboard stats
  getStats: () => apiFetch<DashboardStats>("/mission-control/stats"),

  // Agents
  listAgents: () => apiFetch<Agent[]>("/mission-control/agents"),
  getAgent: (agentId: string) => apiFetch<Agent>(`/mission-control/agents/${agentId}`),
  updateAgent: (agentId: string, data: Partial<Agent>) =>
    apiFetch<Agent>(`/mission-control/agents/${agentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // Tasks
  listTasks: (params?: { status?: string; assignee_id?: string; priority?: string }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.assignee_id) sp.set("assignee_id", params.assignee_id);
    if (params?.priority) sp.set("priority", params.priority);
    const qs = sp.toString();
    return apiFetch<AgentTask[]>(`/mission-control/tasks${qs ? `?${qs}` : ""}`);
  },
  createTask: (data: { id: string; title: string; brief?: string; priority?: string; assignee_id?: string; tags?: string[] }) =>
    apiFetch<AgentTask>("/mission-control/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getTask: (taskId: string) => apiFetch<AgentTask>(`/mission-control/tasks/${taskId}`),
  updateTask: (taskId: string, data: Partial<AgentTask>) =>
    apiFetch<AgentTask>(`/mission-control/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteTask: (taskId: string) =>
    apiFetch(`/mission-control/tasks/${taskId}`, { method: "DELETE" }),

  // Messages
  listMessages: (params?: { agent_id?: string; message_type?: string; task_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.agent_id) sp.set("agent_id", params.agent_id);
    if (params?.message_type) sp.set("message_type", params.message_type);
    if (params?.task_id) sp.set("task_id", params.task_id);
    if (params?.limit) sp.set("limit", String(params.limit));
    const qs = sp.toString();
    return apiFetch<AgentMessage[]>(`/mission-control/messages${qs ? `?${qs}` : ""}`);
  },
  sendMessage: (data: { from_agent_id?: string; to_agent_id?: string; message: string; message_type?: string; task_id?: string }) =>
    apiFetch<AgentMessage>("/mission-control/messages", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Deliverables
  listDeliverables: (params?: { task_id?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.task_id) sp.set("task_id", params.task_id);
    if (params?.status) sp.set("status", params.status);
    const qs = sp.toString();
    return apiFetch<Deliverable[]>(`/mission-control/deliverables${qs ? `?${qs}` : ""}`);
  },
  createDeliverable: (data: { task_id: string; title: string; content?: string; deliverable_type?: string; created_by_agent_id?: string }) =>
    apiFetch<Deliverable>("/mission-control/deliverables", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateDeliverable: (deliverableId: string, status: string, feedback?: string) => {
    const sp = new URLSearchParams({ status });
    if (feedback) sp.set("feedback", feedback);
    return apiFetch(`/mission-control/deliverables/${deliverableId}?${sp.toString()}`, {
      method: "PATCH",
    });
  },

  // Orchestrator view
  getOrchestratorActivity: (hours?: number) =>
    apiFetch<OrchestratorActivity>(`/mission-control/orchestrator${hours ? `?hours=${hours}` : ""}`),

  // Broadcast
  broadcast: (message: string) =>
    apiFetch(`/mission-control/broadcast?message=${encodeURIComponent(message)}`, {
      method: "POST",
    }),
};
