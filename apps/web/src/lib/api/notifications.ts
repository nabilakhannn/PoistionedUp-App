/**
 * Notifications API client — agent-generated notifications for the user.
 */
import { apiFetch } from "./client";

export interface AgentNotification {
  id: string;
  title: string;
  body: string;
  notification_type:
    | "briefing"
    | "reminder"
    | "alert"
    | "suggestion"
    | "insight"
    | "goal_update";
  priority: "low" | "medium" | "high" | "urgent";
  from_agent_id: string | null;
  related_task_id: string | null;
  related_goal_id: string | null;
  status: "unread" | "read" | "dismissed" | "actioned";
  action_url: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
}

export interface UnreadCount {
  count: number;
  by_priority: Record<string, number>;
}

export const notificationsApi = {
  list: (params?: { status?: string; notification_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.notification_type) sp.set("notification_type", params.notification_type);
    if (params?.limit) sp.set("limit", String(params.limit));
    const qs = sp.toString();
    return apiFetch<AgentNotification[]>(`/notifications${qs ? `?${qs}` : ""}`);
  },

  unreadCount: () => apiFetch<UnreadCount>("/notifications/unread-count"),

  markRead: (id: string) =>
    apiFetch(`/notifications/${id}/read`, { method: "PATCH" }),

  dismiss: (id: string) =>
    apiFetch(`/notifications/${id}/dismiss`, { method: "PATCH" }),

  markAllRead: () =>
    apiFetch("/notifications/read-all", { method: "POST" }),

  latestBriefing: () =>
    apiFetch<AgentNotification | null>("/notifications/briefing/latest"),
};
