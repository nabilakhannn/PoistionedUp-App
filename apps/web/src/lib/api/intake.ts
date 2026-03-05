/** Intake API — Slice 97
 *
 * Public shareable form sent to clients before the discovery call.
 */

import { apiFetch } from "./client";

export interface IntakeForm {
  id: string;
  share_token: string;
  client_name?: string;
  business_name?: string;
  industry?: string;
  current_revenue?: string;
  primary_offer?: string;
  offer_price?: string;
  secondary_offers?: string;
  target_audience?: string;
  best_3_clients?: string;
  traffic_sources?: string;
  funnel_status?: string;
  biggest_frustration?: string;
  goals?: string;
  tech_stack?: string;
  timeline?: string;
  additional_notes?: string;
  submitted_at?: string | null;
  created_at?: string;
}

export type IntakeSubmit = Omit<IntakeForm, "id" | "share_token" | "created_at">;

export const intakeApi = {
  /** Create a new intake form for a brand and get the share link */
  create: (brandId: string, clientName?: string) =>
    apiFetch<{ id: string; share_token: string; share_url: string }>(
      "/intake/create",
      { method: "POST", body: JSON.stringify({ brand_id: brandId, client_name: clientName }) }
    ),

  /** SB views the latest submitted form for a brand */
  getMyForm: (brandId: string) =>
    apiFetch<IntakeForm | null>(`/intake/my?brand_id=${brandId}`),
};

/** Public intake API — no auth, direct fetch (no JWT needed) */
export const publicIntakeApi = {
  /** Fetch form schema + current values by share token */
  getForm: async (token: string): Promise<IntakeForm | null> => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "https://api-iota-puce.vercel.app";
    const resp = await fetch(`${baseUrl}/intake/${token}`);
    if (!resp.ok) return null;
    return resp.json();
  },

  /** Client submits the form */
  submit: async (token: string, data: Partial<IntakeSubmit>): Promise<{ status: string; message: string }> => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "https://api-iota-puce.vercel.app";
    const resp = await fetch(`${baseUrl}/intake/${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error("Failed to submit form");
    return resp.json();
  },
};
