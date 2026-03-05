/** Knowledge Documents API — Slice 90
 *
 * Two-tier knowledge base for agents:
 *   scope='system' — app owner SOPs, all users inherit
 *   scope='user'   — per-brand docs (your writing rules, templates, case studies)
 */

import { apiFetch } from "./client";

export type DocType = "writing_sop" | "cold_email" | "framework" | "ad_copy" | "case_study" | "instructions" | "other";
export type Platform = "linkedin" | "youtube" | "twitter" | "email" | "all";

export interface KnowledgeDoc {
  id: string;
  user_id: string | null;
  brand_id: string | null;
  title: string;
  content: string;
  doc_type: DocType;
  platform: Platform;
  scope: "system" | "user";
  agent_scope: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateDocInput {
  brand_id?: string;
  title: string;
  content: string;
  doc_type?: DocType;
  platform?: Platform;
  agent_scope?: string[];
}

export interface UpdateDocInput {
  title?: string;
  content?: string;
  doc_type?: DocType;
  platform?: Platform;
  agent_scope?: string[];
}

export const knowledgeDocsApi = {
  list: (params?: { brand_id?: string; doc_type?: DocType; platform?: Platform }) => {
    const qs = new URLSearchParams();
    if (params?.brand_id) qs.set("brand_id", params.brand_id);
    if (params?.doc_type) qs.set("doc_type", params.doc_type);
    if (params?.platform) qs.set("platform", params.platform);
    const q = qs.toString();
    return apiFetch<KnowledgeDoc[]>(`/knowledge-docs${q ? `?${q}` : ""}`);
  },

  create: (data: CreateDocInput) =>
    apiFetch<KnowledgeDoc>("/knowledge-docs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateDocInput) =>
    apiFetch<KnowledgeDoc>(`/knowledge-docs/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/knowledge-docs/${id}`, { method: "DELETE" }),
};
