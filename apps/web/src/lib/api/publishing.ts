import { apiFetch } from "./client";

export interface PublishResult {
  success: boolean;
  item_id: string;
  platform: string;
  published_url: string | null;
  published_at: string | null;
  error: string | null;
}

export interface RunDueResult {
  published: number;
  failed: number;
  skipped: number;
  errors: { item_id: string; platform?: string; error: string }[];
}

export interface PublishStatus {
  item_id: string;
  status: string;
  published_url: string | null;
  published_at: string | null;
  publish_error: string | null;
  publish_attempted_at: string | null;
}

export const publishingApi = {
  publishItem: (itemId: string) =>
    apiFetch<PublishResult>(`/schedule/${itemId}/publish`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  runDuePosts: () =>
    apiFetch<RunDueResult>("/schedule/run-due", {
      method: "POST",
      body: JSON.stringify({}),
    }),

  getPublishStatus: (itemId: string) =>
    apiFetch<PublishStatus>(`/schedule/${itemId}/publish-status`),
};
