import { apiFetch } from "./client";

export interface ResearchBrief {
  id: string;
  content: string;
  topic_count: number;
  created_at: string;
}

export const researchBriefsApi = {
  getLatest: (brandId: string): Promise<{ brief: ResearchBrief | null }> =>
    apiFetch(`/research/briefs/latest?brand_id=${encodeURIComponent(brandId)}`),
};
