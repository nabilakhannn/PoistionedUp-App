import { apiFetch } from "./client";

export interface Campaign {
  id: string;
  user_id: string;
  brand_id: string;
  name: string;
  description: string;
  platforms: string[];
  content_types: string[];
  total_pieces: number;
  completed_pieces: number;
  approved_pieces: number;
  status: "planning" | "active" | "paused" | "done";
  template_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignCreate {
  brand_id: string;
  name: string;
  description?: string;
  platforms?: string[];
  content_types?: string[];
  total_pieces?: number;
  template_id?: string;
}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  status?: string;
  total_pieces?: number;
  platforms?: string[];
  content_types?: string[];
}

export const campaignsApi = {
  list: (brandId?: string): Promise<Campaign[]> =>
    apiFetch(brandId ? `/campaigns?brand_id=${brandId}` : "/campaigns"),

  get: (id: string): Promise<Campaign> =>
    apiFetch(`/campaigns/${id}`),

  create: (data: CampaignCreate): Promise<Campaign> =>
    apiFetch("/campaigns", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: CampaignUpdate): Promise<Campaign> =>
    apiFetch(`/campaigns/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string): Promise<{ message: string }> =>
    apiFetch(`/campaigns/${id}`, { method: "DELETE" }),

  activate: (id: string): Promise<Campaign> =>
    apiFetch(`/campaigns/${id}/activate`, { method: "POST" }),

  pause: (id: string): Promise<Campaign> =>
    apiFetch(`/campaigns/${id}/pause`, { method: "POST" }),

  incrementCompleted: (id: string): Promise<Campaign> =>
    apiFetch(`/campaigns/${id}/increment-completed`, { method: "POST" }),

  incrementApproved: (id: string): Promise<Campaign> =>
    apiFetch(`/campaigns/${id}/increment-approved`, { method: "POST" }),
};
