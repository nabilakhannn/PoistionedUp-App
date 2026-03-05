/** Content Planning API — Slice 106
 *
 * Jumbo brainstorms with the user to co-create a content plan.
 * User approves topics → VPS executes each one as a separate post.
 */

import { apiFetch } from "./client";

export interface PlanItem {
  topic: string;
  angle: string;
  format: string;
}

export interface BrainstormResponse {
  message: string;
  brand_name: string;
}

export interface PlanChatResponse {
  response: string;
}

export interface ApproveResponse {
  plan_id: string;
  item_count: number;
  status: string;
}

export interface PlanStatusResponse {
  status: "approved" | "executing" | "done" | "failed" | "unknown";
  item_count: number;
  brand_id: string;
}

export const contentPlanningApi = {
  /** Open the planning conversation — Jumbo returns an opening brainstorm message. */
  brainstorm: (brandId: string): Promise<BrainstormResponse> =>
    apiFetch<BrainstormResponse>("/plan/brainstorm", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId }),
    }),

  /** Continue the multi-turn planning conversation. */
  chat: (
    brandId: string,
    messages: { role: string; content: string }[]
  ): Promise<PlanChatResponse> =>
    apiFetch<PlanChatResponse>("/plan/chat", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId, messages }),
    }),

  /** Save the approved plan — VPS picks it up and executes each item. */
  approve: (brandId: string, items: PlanItem[]): Promise<ApproveResponse> =>
    apiFetch<ApproveResponse>("/plan/approve", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId, items }),
    }),

  /** Poll plan execution status. */
  status: (planId: string): Promise<PlanStatusResponse> =>
    apiFetch<PlanStatusResponse>(`/plan/status/${planId}`),
};
