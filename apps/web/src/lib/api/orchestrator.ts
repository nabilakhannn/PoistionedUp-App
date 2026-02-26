/**
 * Orchestrator API client — autonomous task scheduling and execution.
 */
import { apiFetch } from "./client";

// ── Types ─────────────────────────────────────────────────

export interface ScheduleDefinition {
  id: string;
  name: string;
  agent_id: string;
  task_type: string;
  priority: string;
  day_of_week: number;
  hour: number;
}

export interface ScheduleState {
  id: string;
  name: string;
  agent_id: string;
  task_type: string;
  is_due: boolean;
  has_recent_run: boolean;
  last_run: {
    id: string;
    status: string;
    created_at: string;
    completed_at: string | null;
  } | null;
}

export interface PulseResult {
  timestamp: string;
  created_tasks: Record<string, unknown>[];
  skipped: { schedule_id: string; reason: string }[];
  executed: Record<string, unknown>[];
  active_brand: { id: string; name: string } | null;
}

export interface TriggerResult {
  task: Record<string, unknown>;
  execution: Record<string, unknown> | null;
}

export interface OrchestratorExecuteResult {
  status: string;
  task_id: string;
  deliverable_id: string | null;
  error: string | null;
  details: Record<string, unknown>;
}

export interface OrchestratorStatus {
  timestamp: string;
  schedules: ScheduleState[];
  active_tasks: Record<string, unknown>[];
  recent_completed: Record<string, unknown>[];
}

// ── API Methods ───────────────────────────────────────────

export const orchestratorApi = {
  /** Run the orchestrator pulse: check schedules, create & execute due tasks. */
  pulse: (opts: { auto_execute?: boolean; force?: boolean } = {}) =>
    apiFetch<PulseResult>("/orchestrator/pulse", {
      method: "POST",
      body: JSON.stringify({
        auto_execute: opts.auto_execute ?? false,
        force: opts.force ?? false,
      }),
    }),

  /** Manually trigger a specific schedule, ignoring cooldown. */
  trigger: (scheduleId: string, autoExecute: boolean = true) =>
    apiFetch<TriggerResult>("/orchestrator/trigger", {
      method: "POST",
      body: JSON.stringify({
        schedule_id: scheduleId,
        auto_execute: autoExecute,
      }),
    }),

  /** Execute a specific orchestrator task. */
  execute: (taskId: string) =>
    apiFetch<OrchestratorExecuteResult>(`/orchestrator/execute/${taskId}`, {
      method: "POST",
    }),

  /** Get orchestrator status: schedules, active tasks, recent history. */
  status: () => apiFetch<OrchestratorStatus>("/orchestrator/status"),

  /** List all schedule definitions. */
  schedules: () =>
    apiFetch<{ schedules: ScheduleDefinition[] }>("/orchestrator/schedules"),
};
