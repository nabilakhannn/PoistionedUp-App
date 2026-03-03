import { apiFetch } from "./client";

// ── Types ──────────────────────────────────────────────────────────────────

export interface PageSection {
  type: string;
  headline_direction?: string;
  subheadline_direction?: string;
  body_direction?: string;
  cta_text?: string;
  urgency?: string;
  proof_type?: string;
  direction?: string;
  questions?: string[];
}

export interface PageStructure {
  title?: string;
  sections: PageSection[];
  tone?: string;
  color_hint?: string;
  estimated_word_count?: number;
  error?: string;
}

export interface StructureRequest {
  brand_id: string;
  description: string;
  page_goal: string;
  target_audience: string;
  inspiration_url?: string;
}

export interface GenerateRequest {
  brand_id: string;
  description: string;
  structure: PageStructure;
}

export interface GenerateResponse {
  id?: string;
  html: string;
  title: string;
  model_used?: string;
  error?: string;
}

export interface LandingPageTool {
  name: string;
  free_tier: string;
  drag_drop: boolean;
  custom_domain: boolean;
  templates: number;
  score: number;
}

export interface ToolResearchResponse {
  tools: LandingPageTool[];
  source: "live" | "cached";
}

export interface LandingPageRecord {
  id: string;
  brand_id?: string;
  title: string;
  description?: string;
  page_goal?: string;
  model_used?: string;
  created_at: string;
}

export type PageGoal = "capture_email" | "book_call" | "sell_product" | "build_awareness" | "other";

export const PAGE_GOAL_LABELS: Record<PageGoal, string> = {
  capture_email: "Capture Email",
  book_call: "Book a Call",
  sell_product: "Sell a Product",
  build_awareness: "Build Awareness",
  other: "Other",
};

// ── API client ─────────────────────────────────────────────────────────────

export const landingPageApi = {
  researchTools: (): Promise<ToolResearchResponse> =>
    apiFetch<ToolResearchResponse>("/landing-page/tools", { method: "POST" }),

  structurePage: (req: StructureRequest): Promise<PageStructure> =>
    apiFetch<PageStructure>("/landing-page/structure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    }),

  generatePage: (req: GenerateRequest): Promise<GenerateResponse> =>
    apiFetch<GenerateResponse>("/landing-page/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    }),

  listHistory: (brandId: string, limit = 20): Promise<LandingPageRecord[]> =>
    apiFetch<LandingPageRecord[]>(
      `/landing-page/history?brand_id=${encodeURIComponent(brandId)}&limit=${limit}`
    ),
};
