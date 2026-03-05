/** Account Manager API — Slice 98
 *
 * Analyzes client call transcripts and produces 7-category action plans.
 */

import { apiFetch } from "./client";

export type ActionCategory =
  | "content"
  | "brand_profile"
  | "leads"
  | "knowledge"
  | "nurture"
  | "gaps"
  | "deliverable";

export type ActionPriority = "high" | "medium" | "low";

export type ActionAgent =
  | "copywriter"
  | "visual-designer"
  | "profile"
  | "crm"
  | "sequence-builder"
  | "competitor-analyst"
  | "client-deliverables";

export interface ActionItem {
  id: string;
  category: ActionCategory;
  title: string;
  description: string;
  agent: ActionAgent;
  priority: ActionPriority;
  approved: boolean | null;
  executed: boolean;
  result: string | null;
}

export interface AccountManagerSession {
  id: string;
  user_id: string;
  brand_id: string;
  intake_form_id?: string;
  client_name: string;
  call_date: string;
  call_number: number;
  summary: string;
  cross_call_themes: string[];
  action_plan: ActionItem[];
  status: "pending_review" | "approved" | "executing" | "completed";
  created_at: string;
  completed_at?: string;
}

export const accountManagerApi = {
  /** Analyze a transcript and create an action plan session */
  analyze: (data: {
    brand_id: string;
    transcript: string;
    call_date?: string;
    intake_form_id?: string;
  }) =>
    apiFetch<AccountManagerSession>("/account-manager/analyze", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** List all sessions for a brand */
  listSessions: (brandId: string) =>
    apiFetch<AccountManagerSession[]>(`/account-manager/sessions?brand_id=${brandId}`),

  /** Get a single session */
  getSession: (sessionId: string) =>
    apiFetch<AccountManagerSession>(`/account-manager/sessions/${sessionId}`),

  /** Update action items (approve/deny) */
  updateSession: (
    sessionId: string,
    actions: ActionItem[],
    status?: string
  ) =>
    apiFetch<{ session_id: string; status: string }>(
      `/account-manager/sessions/${sessionId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ actions, status }),
      }
    ),
};
