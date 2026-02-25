/** Mission Control shared constants */

export const ROLE_TYPE_BADGES: Record<string, { label: string; color: string }> = {
  lead: { label: "LEAD", color: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
  specialist: { label: "SPC", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  integrator: { label: "INT", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
};

export const STATUS_COLORS: Record<string, { dot: string; label: string; bg: string }> = {
  idle: { dot: "bg-zinc-400", label: "IDLE", bg: "bg-zinc-500/20 text-zinc-400" },
  working: { dot: "bg-green-400", label: "WORKING", bg: "bg-green-500/20 text-green-400" },
  error: { dot: "bg-red-400", label: "ERROR", bg: "bg-red-500/20 text-red-400" },
  paused: { dot: "bg-amber-400", label: "PAUSED", bg: "bg-amber-500/20 text-amber-400" },
};

export const PRIORITY_COLORS: Record<string, string> = {
  P0: "border-l-red-500",
  P1: "border-l-amber-500",
  P2: "border-l-blue-500",
  P3: "border-l-zinc-500",
};

export const TASK_STATUS_COLUMNS = [
  { key: "backlog", label: "INBOX", color: "text-zinc-400" },
  { key: "assigned", label: "ASSIGNED", color: "text-amber-400" },
  { key: "in_progress", label: "IN PROGRESS", color: "text-blue-400" },
  { key: "review", label: "REVIEW", color: "text-purple-400" },
  { key: "ready", label: "READY", color: "text-green-400" },
  { key: "done", label: "DONE", color: "text-emerald-400" },
];

export const TASK_FILTER_TABS = [
  { key: "all", label: "All" },
  { key: "backlog", label: "Inbox" },
  { key: "assigned", label: "Assigned" },
  { key: "in_progress", label: "Active" },
  { key: "review", label: "Review" },
  { key: "done", label: "Done" },
  { key: "ready", label: "Waiting" },
];

export const MESSAGE_TYPE_ICONS: Record<string, string> = {
  chat: "💬",
  delegation: "📋",
  status: "📡",
  deliverable: "📦",
  escalation: "🚨",
  broadcast: "📢",
};
