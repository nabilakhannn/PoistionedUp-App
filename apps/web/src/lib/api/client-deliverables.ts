/** Client Deliverables API — Slice 98
 *
 * Proposals, landing pages, nurture sequences. All have share tokens for public preview.
 */

import { apiFetch } from "./client";

export type DeliverableType =
  | "proposal"
  | "landing_page"
  | "ad_creative"
  | "nurture_sequence";

export interface NurtureEmail {
  email_number: number;
  day: number;
  subject: string;
  body: string;
  cta: string;
}

export type ProposalStatus =
  | "draft"
  | "sent"
  | "accepted"
  | "rejected"
  | "closed_won"
  | "closed_lost";

export interface ClientDeliverable {
  id: string;
  title: string;
  deliverable_type: DeliverableType;
  version: number;
  client_brand: boolean;
  share_token: string;
  content: string;
  metadata?: Record<string, unknown>;
  proposal_status?: ProposalStatus;
  deal_value?: number;
  created_at: string;
}

export const clientDeliverablesApi = {
  /** Generate a proposal from an account manager session */
  generateProposal: (sessionId: string, brandId: string) =>
    apiFetch<{
      deliverable_id: string;
      share_token: string;
      version: number;
      content: string;
    }>("/deliverables/proposal", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, brand_id: brandId }),
    }),

  /** Generate a landing page from the brand dossier */
  generateLandingPage: (brandId: string) =>
    apiFetch<{
      deliverable_id: string;
      share_token: string;
      version: number;
      content: string;
    }>("/deliverables/landing-page", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId }),
    }),

  /** Generate a 5-email nurture sequence */
  generateNurtureSequence: (brandId: string, leadContext: string) =>
    apiFetch<{
      deliverable_id: string;
      share_token: string;
      version: number;
      sequence: NurtureEmail[];
    }>("/deliverables/nurture-sequence", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId, lead_context: leadContext }),
    }),

  /** List all deliverables for a brand */
  list: (brandId: string, deliverableType?: DeliverableType) => {
    const params = new URLSearchParams({ brand_id: brandId });
    if (deliverableType) params.set("deliverable_type", deliverableType);
    return apiFetch<ClientDeliverable[]>(`/deliverables?${params}`);
  },

  /** Get a single deliverable */
  get: (deliverableId: string) =>
    apiFetch<ClientDeliverable>(`/deliverables/${deliverableId}`),

  /** Public share URL (no auth) */
  shareUrl: (shareToken: string): string => {
    const base = process.env.NEXT_PUBLIC_API_URL || "https://api-iota-puce.vercel.app";
    return `${base}/share/${shareToken}`;
  },

  /** Update proposal lifecycle status (optionally with deal value) */
  updateStatus: (deliverableId: string, proposalStatus: ProposalStatus, dealValue?: number) =>
    apiFetch<{ ok: boolean; proposal_status: string; deal_value?: number }>(
      `/deliverables/${deliverableId}/status`,
      {
        method: "PATCH",
        body: JSON.stringify({
          proposal_status: proposalStatus,
          ...(dealValue !== undefined ? { deal_value: dealValue } : {}),
        }),
      },
    ),

  /** Regenerate a deliverable (creates new version) */
  regenerate: (deliverableId: string) =>
    apiFetch<{
      deliverable_id: string;
      share_token: string;
      version: number;
      content: string;
    }>(`/deliverables/${deliverableId}/regenerate`, { method: "POST" }),
};
