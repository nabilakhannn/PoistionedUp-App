/**
 * Schedule API -- content calendar and kanban board.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

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

// ── API Methods ──────────────────────────────────────────

export const scheduleApi = {
  getBoard: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<KanbanBoard>(`/schedule${qs}`);
  },

  getCalendar: (start: string, end: string, brandId?: string) => {
    const params = new URLSearchParams();
    params.set("start", start);
    params.set("end", end);
    if (brandId) params.set("brand_id", brandId);
    return apiFetch<ScheduledItem[]>(
      `/schedule/calendar?${params.toString()}`
    );
  },

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
    brand_id?: string;
  }) =>
    apiFetch<ScheduledItem>("/schedule", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  importFromWorkflow: (workflowId: string) =>
    apiFetch<ImportResult>(`/schedule/import/${workflowId}`, {
      method: "POST",
    }),

  update: (id: string, data: Partial<ScheduledItem>) =>
    apiFetch<ScheduledItem>(`/schedule/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  move: (
    id: string,
    status: string,
    columnOrder: number,
    brandId?: string
  ) =>
    apiFetch<ScheduledItem>(`/schedule/${id}/move`, {
      method: "PATCH",
      body: JSON.stringify({
        status,
        column_order: columnOrder,
        brand_id: brandId,
      }),
    }),

  delete: (id: string, brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<void>(`/schedule/${id}${qs}`, { method: "DELETE" });
  },

  createFromResearch: (sessionId: string, scheduleDates: boolean = false) =>
    apiFetch<{ created: number; items: ScheduledItem[]; message: string }>(
      `/schedule/from-research/${sessionId}`,
      {
        method: "POST",
        body: JSON.stringify({ schedule_dates: scheduleDates }),
      }
    ),
};
