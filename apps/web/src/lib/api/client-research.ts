/** Client Research API — Slice 97
 *
 * Runs deep 5-layer Brand Researcher agent (LinkedIn, pain points, Hormozi, competitors).
 */

import { apiFetch } from "./client";

export interface HormoziFramework {
  dream_outcome: string;
  perceived_likelihood: string;
  time_to_result: string;
  effort_sacrifice: string;
  guarantee: string;
  risk_reversals: string[];
}

export interface ContentAngle {
  hook: string;
  angle_type: "anxiety" | "benefit" | "story" | "competitor";
  driven_by: string;
  offer_connection: string;
}

export interface Competitor {
  name: string;
  positioning: string;
  gap: string;
}

export interface Transformation {
  zero_state: string;
  dream_state: string;
  journey: string;
}

export interface YourStory {
  background: string;
  growth_achievements: string;
  future_goals: string;
  mission: string;
}

export interface FalseBelief {
  belief: string;
  counter_story: string;
}

export interface BeliefFramework {
  belief_statement: string;
  false_beliefs: FalseBelief[];
}

export interface CustomerSegment {
  segment: string;
  age: string;
  problem: string;
}

export interface ClientDossier {
  // Section 1 — Niche Market
  content_pillars: string[];
  voice_adjectives: string[];
  ica_summary: string;
  market_gap?: string;
  customer_segments?: CustomerSegment[];
  relevance_topics?: string[];
  power_words?: string[];
  industry_lingo?: string[];

  // Section 2 — Transformation
  transformation?: Transformation;

  // Section 3 — New Opportunity
  uvps?: string[];
  tagline?: string;
  niche_statement?: string;

  // Section 4 — Metaphors
  metaphors?: string[];

  // Section 5 — Content Strategy (via content_pillars above)

  // Section 6 — Your Story
  your_story?: YourStory;

  // Section 7 — Belief Framework
  belief_framework?: BeliefFramework;

  // Section 8 — Revenue Streams (via hormozi)
  hormozi: HormoziFramework;

  // Pain & benefit intelligence
  anxiety_list: string[];
  benefit_list: string[];
  emotional_pain_journal: string;
  emotional_win_journal: string;

  // Competitor intelligence
  competitors: Competitor[];
  competitor_gap: string;

  // First week content
  first_week_angles: ContentAngle[];

  // Meta
  research_source?: { linkedin_url: string; website_url: string };
  research_completed_at?: string;
}

export interface ClientReport {
  brand_id: string;
  name: string;
  is_client_brand: boolean;
  profile: Partial<ClientDossier>;
}

export type RefreshSection =
  | "hormozi"
  | "competitors"
  | "anxiety_list"
  | "benefit_list"
  | "first_week_angles"
  | "emotional_pain_journal"
  | "emotional_win_journal"
  | "transformation"
  | "uvps"
  | "metaphors"
  | "your_story"
  | "belief_framework"
  | "power_words"
  | "market_gap";

export const clientResearchApi = {
  run: (
    brandId: string,
    data: {
      linkedin_url: string;
      website_url?: string;
      offer_description?: string;
      best_clients?: string;
      content_goal?: string;
    }
  ) =>
    apiFetch<{ status: string; brand_id: string; dossier: ClientDossier }>(
      "/client-research/run",
      { method: "POST", body: JSON.stringify({ brand_id: brandId, ...data }) }
    ),

  getReport: (brandId: string) =>
    apiFetch<ClientReport>(`/client-research/report/${brandId}`),

  refresh: (brandId: string, section: RefreshSection) =>
    apiFetch<{ status: string; brand_id: string } & Record<string, unknown>>(
      `/client-research/refresh/${brandId}`,
      { method: "POST", body: JSON.stringify({ section }) }
    ),
};
