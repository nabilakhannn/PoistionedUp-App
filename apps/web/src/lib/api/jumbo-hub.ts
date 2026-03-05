/** Jumbo Hub API — Slice 107
 *
 * Persistent multi-turn chat with Jumbo (general-purpose AI partner).
 * Conversations are per-brand, stored server-side with full history.
 */

import { apiFetch } from "./client";

export interface ChatMessage {
  role: "user" | "jumbo";
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  brand_id: string;
  messages: ChatMessage[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  brand_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  title: string;
}

export const jumboHubApi = {
  /** Create a new conversation for a brand. */
  createConversation: (brandId: string) =>
    apiFetch<Conversation>("/hub/conversations", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId }),
    }),

  /** List active conversations for a brand (most recent first). */
  listConversations: (brandId: string, limit = 20) =>
    apiFetch<{ conversations: ConversationSummary[] }>(
      `/hub/conversations?brand_id=${brandId}&limit=${limit}`
    ),

  /** Get full conversation with all messages. */
  getConversation: (conversationId: string) =>
    apiFetch<Conversation>(`/hub/conversations/${conversationId}`),

  /** Send a message and get Jumbo's response. */
  chat: (conversationId: string, message: string) =>
    apiFetch<ChatResponse>(`/hub/conversations/${conversationId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  /** Archive (soft delete) a conversation. */
  archiveConversation: (conversationId: string) =>
    apiFetch<{ ok: boolean }>(`/hub/conversations/${conversationId}/archive`, {
      method: "PATCH",
    }),

  /** Save text as an agent_memory note. */
  saveAsNote: (brandId: string, content: string, title = "") =>
    apiFetch<{ id: string }>("/hub/save-note", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId, content, title }),
    }),
};
