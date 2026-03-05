// ── Shared types for the Content Composer ──

export interface TopicCandidate {
  id: string;
  title: string;
  audience_pain: string;
  opportunity_score: number;
  risk_flags: string[];
  sources: string[];
  score_breakdown: Record<string, number>;
  why_now: string;
}

export interface HookCandidate {
  id: string;
  hook_text: string;
  hook_type: string;
  total_score: number;
  score_breakdown: Record<string, number>;
}

export const STEP_ORDER = [
  "signal_research",
  "gap_analysis",
  "topic_selection",
  "hook_lab",
  "script_generation",
  "editor",
  "testing",
  "approval",
] as const;

export const STEP_LABELS: Record<string, string> = {
  signal_research: "Researching signals",
  gap_analysis: "Analyzing gaps",
  topic_selection: "Selecting topics",
  hook_lab: "Generating hooks",
  script_generation: "Writing scripts",
  editor: "Editing content",
  testing: "Running quality tests",
  approval: "Awaiting approval",
};

export const PLATFORM_LABELS: Record<string, string> = {
  youtube: "YouTube",
  linkedin: "LinkedIn",
  twitter: "Twitter/X",
  short_form: "Short-form",
};
