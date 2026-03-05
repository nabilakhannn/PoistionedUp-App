/** Experience Journal API — Slice 90 + 039 (usage tracking + pin control)
 *
 * Captures user's real experiences: calls, transcripts, notes, case studies.
 * Agents read these to ground content in real experience.
 *
 * New in 039:
 *  - times_used / last_used_at: agent usage tracking (auto-rotates to fresh stories)
 *  - pinned: user can pin entries to always include them in pipeline writes
 *  - pin(): toggle pin on an entry
 *  - suggest(): ask AI which entries it would use for a given topic
 */

import { apiFetch } from "./client";

export type SourceType = "call_recording" | "transcript" | "note" | "case_study";

export interface JournalEntry {
  id: string;
  brand_id: string;
  title: string | null;
  source_type: SourceType;
  raw_content: string;
  insights: { title: string; summary: string; tags: string[] }[];
  tags: string[];
  created_at: string;
  times_used: number;
  last_used_at: string | null;
  pinned: boolean;
}

export interface CreateJournalInput {
  brand_id: string;
  title?: string;
  source_type?: SourceType;
  raw_content: string;
  tags?: string[];
}

export interface SuggestResult {
  suggested_ids: string[];
  entries: JournalEntry[];
  reasoning: string;
}

export const journalApi = {
  list: (brandId: string, params?: { source_type?: SourceType; limit?: number }) => {
    const qs = new URLSearchParams({ brand_id: brandId });
    if (params?.source_type) qs.set("source_type", params.source_type);
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<JournalEntry[]>(`/journal?${qs.toString()}`);
  },

  create: (data: CreateJournalInput) =>
    apiFetch<JournalEntry>("/journal", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/journal/${id}`, { method: "DELETE" }),

  /** Toggle pinned flag. Pinned entries are always included in pipeline Phase 2. */
  pin: (id: string) =>
    apiFetch<JournalEntry>(`/journal/${id}/pin`, { method: "PATCH" }),

  /** Ask AI which entries it would use for a given topic/research brief. */
  suggest: (brandId: string, topic?: string, limit?: number) => {
    const qs = new URLSearchParams({ brand_id: brandId });
    if (topic) qs.set("topic", topic);
    if (limit) qs.set("limit", String(limit));
    return apiFetch<SuggestResult>(`/journal/suggest?${qs.toString()}`);
  },
};
