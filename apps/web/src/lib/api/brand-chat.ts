/** Brand Chat API — Slice 100
 *
 * Sends messages to Jumbo with the full 8-section brand dossier pre-loaded.
 * Jumbo generates: hooks, posts, nurture sequences, offer outlines, etc.
 */

import { apiFetch } from "./client";

export interface BrandChatResponse {
  response: string;
  brand_id: string;
  brand_name: string;
}

export const QUICK_ACTIONS = [
  {
    id: "hooks",
    label: "30 Hooks",
    emoji: "📎",
    prompt:
      "Generate 30 content hooks organized by type (anxiety, benefit, story, competitor, belief, metaphor) — 5 per type. Each hook must be specific to this client's niche, voice, and dossier. Start each hook with the exact opening line.",
  },
  {
    id: "nurture",
    label: "Nurture Sequence",
    emoji: "📧",
    prompt:
      "Write a 5-email nurture sequence for cold leads in this client's niche. Use their emotional pain journal and benefit list directly. Each email: Subject Line, Body (200-300 words), CTA. Sequence arc: Pain → Empathy → Insight → Proof → Offer.",
  },
  {
    id: "offer",
    label: "Offer Outline",
    emoji: "💎",
    prompt:
      "Create a Grand Slam Offer outline using this client's UVPs, dream outcome, guarantee, and tagline. Use the Hormozi Value Equation framework. Include: Headline, Dream Outcome, Perceived Likelihood (proof points), Time to Result, Effort Reduction, Guarantee, Risk Reversals, and Pricing Stack.",
  },
  {
    id: "posts",
    label: "5 LinkedIn Posts",
    emoji: "💬",
    prompt:
      "Write 5 LinkedIn posts for this client. One per angle type: anxiety, benefit, story, competitor, belief. Max 3000 chars each. Use their exact voice adjectives and power words. Format: Hook → Body → CTA. Make each post platform-native — no hashtag spam, no emoji overload.",
  },
  {
    id: "comments",
    label: "Comment Drafts",
    emoji: "🗣",
    prompt:
      "Write 5 thoughtful comment drafts this client can use to engage in their niche community. Each comment should position them as a thought leader without being promotional. Reference their belief framework and niche vocabulary. 3-5 sentences each.",
  },
  {
    id: "calendar",
    label: "90-Day Calendar",
    emoji: "📅",
    prompt:
      "Create a 90-day content calendar with 3 posts per week (39 posts total). For each week: Week Theme, then 3 rows with: Day, Hook Type, Angle, Platform, Format (post/carousel/video script). Align the arc with: Month 1 = Awareness, Month 2 = Authority, Month 3 = Conversion.",
  },
] as const;

export type QuickActionId = (typeof QUICK_ACTIONS)[number]["id"];

export const brandChatApi = {
  send: (brandId: string, message: string) =>
    apiFetch<BrandChatResponse>(`/brand-chat/${brandId}`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
