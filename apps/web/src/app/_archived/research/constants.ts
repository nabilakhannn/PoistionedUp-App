/* ────────────────────────────────────────────────────────
   Research Feed: Types & Constants
   ──────────────────────────────────────────────────────── */

export type Platform = "all" | "reddit" | "linkedin" | "youtube" | "tiktok";

export interface FeedCard {
  id: string;
  title: string;
  snippet: string;
  url: string;
  source: Platform;
  author: string;
  date: string;
  views: string;
  likes: string;
  comments: string;
  shares: string;
}

export const PLATFORMS: { id: Platform; label: string; color: string; dotColor: string }[] = [
  { id: "all", label: "All", color: "text-zinc-300", dotColor: "bg-blue-400" },
  { id: "reddit", label: "Reddit", color: "text-orange-400", dotColor: "bg-orange-400" },
  { id: "linkedin", label: "LinkedIn", color: "text-blue-400", dotColor: "bg-blue-500" },
  { id: "youtube", label: "YouTube", color: "text-red-400", dotColor: "bg-red-500" },
  { id: "tiktok", label: "TikTok", color: "text-pink-400", dotColor: "bg-pink-500" },
];

export const SORT_OPTIONS = [
  { id: "relevance", label: "Relevance" },
  { id: "views", label: "Views" },
  { id: "recent", label: "Recent" },
];

export const PLATFORM_COLORS: Record<string, string> = {
  reddit: "border-l-orange-500",
  linkedin: "border-l-blue-500",
  youtube: "border-l-red-500",
  tiktok: "border-l-pink-500",
  web: "border-l-zinc-500",
  all: "border-l-blue-400",
};

export const PLATFORM_ICONS: Record<string, string> = {
  reddit: "🟠",
  linkedin: "🔵",
  youtube: "🔴",
  tiktok: "🩷",
  web: "🌐",
};

export const SEARCH_SUGGESTIONS = [
  "personal branding tips",
  "AI automation tools",
  "content creation strategy",
  "solopreneur growth",
  "YouTube hooks that work",
];
