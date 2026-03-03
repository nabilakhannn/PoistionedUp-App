/**
 * Ad Creative API — bulk ad variation generation from brand research.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface AdVariation {
  id: string;
  hook_type: string;
  hook_angle: string;
  headline: string;
  primary_text: string;
  cta: string;
  platform: string;
}

export interface AdGenerateRequest {
  session_id: string;
  hook_types?: string[];
  platforms?: string[];
  count_per_hook?: number;
}

export interface AdGenerateResponse {
  deliverable_id: string;
  total_count: number;
  variations_by_hook: Record<string, AdVariation[]>;
  hook_errors?: Record<string, string>; // hook_type → error message, empty when all succeeded
  brand_name: string;
  niche: string;
}

export interface AdStageResponse {
  staged_count: number;
  scheduled_item_ids: string[];
}

export interface AdApprovalRequest {
  approved_ids: string[];
  dismissed_ids: string[];
}

// ── Constants ─────────────────────────────────────────────

export const HOOK_TYPES = [
  { value: "pain", label: "Pain Points" },
  { value: "outcome", label: "Outcome / Aspiration" },
  { value: "objection", label: "Objection Busting" },
  { value: "social_proof", label: "Social Proof" },
  { value: "curiosity", label: "Curiosity Gap" },
] as const;

export const AD_PLATFORMS = [
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "linkedin", label: "LinkedIn" },
] as const;

// ── API Methods ──────────────────────────────────────────

export const adCreativeApi = {
  generate: (brandId: string, body: AdGenerateRequest) =>
    apiFetch<AdGenerateResponse>(
      `/brands/${brandId}/ad-creative/generate`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),

  stage: (brandId: string, deliverableId: string, variationIds: string[]) =>
    apiFetch<AdStageResponse>(
      `/brands/${brandId}/ad-creative/${deliverableId}/stage`,
      {
        method: "POST",
        body: JSON.stringify({ variation_ids: variationIds }),
      }
    ),

  patchApprovals: (brandId: string, deliverableId: string, body: AdApprovalRequest) =>
    apiFetch<{ ok: boolean; approved_count: number; dismissed_count: number }>(
      `/brands/${brandId}/ad-creative/${deliverableId}/approvals`,
      {
        method: "PATCH",
        body: JSON.stringify(body),
      }
    ),
};
