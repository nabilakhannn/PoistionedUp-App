/** Content Stages API — Slice 90 */

import { apiFetch } from "./client";

export interface ContentStage {
  id: string;
  brand_id: string;
  name: string;
  color: string;
  position: number;
  stage_type: "auto" | "manual";
  agent_id: string | null;
  is_default: boolean;
  created_at: string;
}

export interface CreateStageInput {
  brand_id: string;
  name: string;
  color?: string;
  stage_type?: "auto" | "manual";
  agent_id?: string | null;
}

export interface UpdateStageInput {
  name?: string;
  color?: string;
  stage_type?: "auto" | "manual";
  agent_id?: string | null;
}

export const stagesApi = {
  list: (brandId: string) =>
    apiFetch<ContentStage[]>(`/stages?brand_id=${encodeURIComponent(brandId)}`),

  create: (data: CreateStageInput) =>
    apiFetch<ContentStage>("/stages", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateStageInput) =>
    apiFetch<ContentStage>(`/stages/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/stages/${id}`, { method: "DELETE" }),

  reorder: (brandId: string, order: string[]) =>
    apiFetch<{ ok: boolean; reordered: number }>("/stages/reorder", {
      method: "PUT",
      body: JSON.stringify({ brand_id: brandId, order }),
    }),
};
