/* ────────────────────────────────────────────────────────
   Content Dashboard: Constants & Helpers
   ──────────────────────────────────────────────────────── */

export const STATUS_CONFIG: Record<string, { bg: string; text: string; label: string; dot: string }> = {
  queued: { bg: "bg-zinc-800", text: "text-zinc-300", label: "Queued", dot: "bg-zinc-400" },
  running: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Running", dot: "bg-blue-400 animate-pulse" },
  awaiting_topic: { bg: "bg-yellow-500/15", text: "text-yellow-400", label: "Pick Topic", dot: "bg-yellow-400" },
  awaiting_hook: { bg: "bg-yellow-500/15", text: "text-yellow-400", label: "Pick Hook", dot: "bg-yellow-400" },
  awaiting_approval: { bg: "bg-purple-500/15", text: "text-purple-400", label: "Review", dot: "bg-purple-400" },
  approved: { bg: "bg-green-500/15", text: "text-green-400", label: "Done", dot: "bg-green-400" },
  completed: { bg: "bg-green-500/15", text: "text-green-400", label: "Done", dot: "bg-green-400" },
  rejected: { bg: "bg-red-500/15", text: "text-red-400", label: "Rejected", dot: "bg-red-400" },
  failed: { bg: "bg-red-500/15", text: "text-red-400", label: "Failed", dot: "bg-red-400" },
};

export const PLATFORM_CONFIG: Record<string, { label: string; color: string }> = {
  youtube: { label: "YouTube", color: "text-red-400" },
  linkedin: { label: "LinkedIn", color: "text-blue-400" },
  twitter: { label: "Twitter/X", color: "text-zinc-300" },
  short_form: { label: "Short-form", color: "text-pink-400" },
  tiktok: { label: "TikTok", color: "text-pink-400" },
};

export const OBJECTIVE_CONFIG: Record<string, { label: string; color: string; border: string }> = {
  personal_branding: { label: "Branding", color: "text-violet-400", border: "border-l-violet-500" },
  sales: { label: "Sales", color: "text-emerald-400", border: "border-l-emerald-500" },
  grow_audience: { label: "Growth", color: "text-blue-400", border: "border-l-blue-500" },
  educate: { label: "Education", color: "text-amber-400", border: "border-l-amber-500" },
  entertainment: { label: "Entertainment", color: "text-pink-400", border: "border-l-pink-500" },
};

export const CONTENT_TYPE_CONFIG: Record<string, { label: string; emoji: string }> = {
  educational: { label: "Educational", emoji: "📚" },
  storytelling: { label: "Story", emoji: "📖" },
  opinion: { label: "Hot Take", emoji: "🔥" },
  how_to: { label: "How-To", emoji: "🛠" },
  listicle: { label: "Listicle", emoji: "📝" },
  contrarian: { label: "Contrarian", emoji: "💥" },
  case_study: { label: "Case Study", emoji: "📊" },
  behind_scenes: { label: "BTS", emoji: "🎬" },
};

export type StatusFilter = "all" | "active" | "completed" | "failed";

export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function getStepProgress(step: string): number {
  const steps: Record<string, number> = {
    signal_research: 12,
    gap_analysis: 25,
    topic_selection: 37,
    hook_lab: 50,
    script_generation: 62,
    editor: 75,
    testing: 87,
    approval: 95,
  };
  return steps[step] || 50;
}
