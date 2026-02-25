/**
 * Inspo Boards API -- boards and items CRUD.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface InspoBoardSummary {
  id: string;
  user_id: string;
  brand_id: string | null;
  name: string;
  description: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface InspoItemDetail {
  id: string;
  board_id: string;
  user_id: string;
  content_type: "text" | "link" | "image" | "video" | "voice_note";
  content_text: string | null;
  source_url: string | null;
  source_tag: string | null;
  intent_note: string | null;
  media_path: string | null;
  tags: string[];
  is_starred: boolean;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface InspoBoardDetail extends InspoBoardSummary {
  items: InspoItemDetail[];
}

// ── API Methods ──────────────────────────────────────────

export const inspoApi = {
  listBoards: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<InspoBoardSummary[]>(`/inspo/boards${qs}`);
  },

  createBoard: (data: {
    name: string;
    description?: string;
    brand_id?: string;
  }) =>
    apiFetch<InspoBoardSummary>("/inspo/boards", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getBoard: (boardId: string) =>
    apiFetch<InspoBoardDetail>(`/inspo/boards/${boardId}`),

  updateBoard: (
    boardId: string,
    data: { name?: string; description?: string; brand_id?: string }
  ) =>
    apiFetch<InspoBoardSummary>(`/inspo/boards/${boardId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteBoard: (boardId: string) =>
    apiFetch<void>(`/inspo/boards/${boardId}`, { method: "DELETE" }),

  listItems: (boardId: string, starredOnly?: boolean, tag?: string) => {
    const params = new URLSearchParams();
    if (starredOnly) params.set("starred_only", "true");
    if (tag) params.set("tag", tag);
    const qs = params.toString();
    return apiFetch<InspoItemDetail[]>(
      `/inspo/boards/${boardId}/items${qs ? `?${qs}` : ""}`
    );
  },

  createItem: (
    boardId: string,
    data: {
      content_type: string;
      content_text?: string;
      source_url?: string;
      source_tag?: string;
      intent_note?: string;
      tags?: string[];
      is_starred?: boolean;
      metadata?: Record<string, any>;
    }
  ) =>
    apiFetch<InspoItemDetail>(`/inspo/boards/${boardId}/items`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getItem: (itemId: string) =>
    apiFetch<InspoItemDetail>(`/inspo/items/${itemId}`),

  updateItem: (
    itemId: string,
    data: {
      content_type?: string;
      content_text?: string;
      source_url?: string;
      source_tag?: string;
      intent_note?: string;
      tags?: string[];
      is_starred?: boolean;
      metadata?: Record<string, any>;
    }
  ) =>
    apiFetch<InspoItemDetail>(`/inspo/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteItem: (itemId: string) =>
    apiFetch<void>(`/inspo/items/${itemId}`, { method: "DELETE" }),

  toggleStar: (itemId: string) =>
    apiFetch<InspoItemDetail>(`/inspo/items/${itemId}/star`, {
      method: "PATCH",
    }),
};
