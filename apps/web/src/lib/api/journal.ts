/** Experience Journal API — Slice 90
 *
 * Captures user's real experiences: calls, transcripts, notes, case studies.
 * Agents read these to ground content in real experience.
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
}

export interface CreateJournalInput {
  brand_id: string;
  title?: string;
  source_type?: SourceType;
  raw_content: string;
  tags?: string[];
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
};
