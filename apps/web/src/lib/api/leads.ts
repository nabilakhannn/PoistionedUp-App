/** Leads API — Slice 95
 *
 * Lead Gen CRM (Clay/Apollo-style) with 3-engine enrichment + BANT scoring.
 * Follows the stages.ts + journal.ts pattern.
 */

import { apiFetch } from "./client";

export interface SequenceMessage {
  label: string;
  day: number;
  channel: "linkedin" | "email";
  message: string;
  sent_at: string | null;
}

export interface LeadEnrichment {
  professional_topics: string[];
  recent_achievements: string[];
  hiring_signals: string[];
  pain_points: string[];
  company_changes: string[];
  industries_served: string[];
  growth_signals: string[];
  last_enriched_at?: string;
}

export interface OutreachDraft {
  linkedin_dm?: string;
  cold_email?: { subject: string; body: string };
}

export type LeadStatus = "cold" | "warm" | "hot" | "customer" | "disqualified";
export type LeadSource = "manual" | "generated" | "imported";

export interface Lead {
  id: string;
  user_id: string;
  brand_id: string;
  full_name: string;
  title: string | null;
  company: string | null;
  linkedin_url: string | null;
  company_website: string | null;
  location: string | null;
  email: string | null;
  twitter_handle: string | null;
  status: LeadStatus;
  source: LeadSource;
  enrichment: LeadEnrichment;
  bant_score: number; // 0-4
  notes: string | null;
  transcript: string | null;
  icebreaker: string | null;
  outreach_draft: OutreachDraft;
  sequence: SequenceMessage[];
  last_enriched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateLeadInput {
  brand_id: string;
  full_name: string;
  title?: string;
  company?: string;
  email?: string;
  linkedin_url?: string;
  company_website?: string;
  location?: string;
  notes?: string;
}

export interface UpdateLeadInput {
  status?: LeadStatus;
  notes?: string;
  transcript?: string;
  icebreaker?: string;
  sequence?: SequenceMessage[];
}

export interface BatchEnrichItem {
  full_name: string;
  company?: string;
  linkedin_url?: string;
  email?: string;
}

export const leadsApi = {
  list: (brandId: string, status?: LeadStatus) => {
    const qs = new URLSearchParams({ brand_id: brandId });
    if (status) qs.set("status", status);
    return apiFetch<Lead[]>(`/leads?${qs}`);
  },

  create: (data: CreateLeadInput) =>
    apiFetch<Lead>("/leads", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  generate: (brandId: string, count = 10) =>
    apiFetch<Lead[]>("/leads/generate", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId, count }),
    }),

  batchEnrich: (brandId: string, leads: BatchEnrichItem[]) =>
    apiFetch<Lead[]>("/leads/batch-enrich", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId, leads }),
    }),

  enrich: (id: string) =>
    apiFetch<Lead>(`/leads/enrich/${id}`, { method: "POST" }),

  generateOutreach: (id: string) =>
    apiFetch<Lead>(`/leads/outreach/${id}`, { method: "POST" }),

  update: (id: string, data: UpdateLeadInput) =>
    apiFetch<Lead>(`/leads/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  remove: (id: string) =>
    apiFetch<void>(`/leads/${id}`, { method: "DELETE" }),

  /** 4-stage ICP research using Sales Lead Research System Prompt methodology */
  icpResearch: (
    brandId: string,
    overrides?: { product_name?: string; pricing?: string; platform?: string; lead_database?: string; scraping_tool?: string }
  ) =>
    apiFetch<{
      stages: Array<{ id: number; name: string; status: string; result: Record<string, unknown> }>;
      brand_id: string;
    }>("/leads/icp-research", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId, ...overrides }),
    }),

  /** Get the ICP methodology template text */
  icpMethodology: () =>
    apiFetch<{ content: string; title: string }>("/leads/icp-methodology"),

  /** Lightweight counts for the Morning Briefing home screen */
  getLeadsPulse: (brandId: string) =>
    apiFetch<{ new_leads: number; unreviewed: number; active_sequences: number }>(
      `/leads/pulse?brand_id=${encodeURIComponent(brandId)}`
    ),

  /** Downloads .xlsx file — Instantly.ai-compatible export */
  exportXlsx: async (brandId: string): Promise<void> => {
    const { createClient } = await import("@/lib/supabase/client");
    const { API_BASE } = await import("./client");
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token ?? "";
    const res = await fetch(
      `${API_BASE}/leads/export?brand_id=${encodeURIComponent(brandId)}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "leads.xlsx";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};
