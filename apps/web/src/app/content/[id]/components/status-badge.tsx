"use client";

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-zinc-700/60 text-zinc-300",
  running: "bg-blue-500/20 text-blue-400",
  awaiting_topic: "bg-yellow-500/20 text-yellow-400",
  awaiting_hook: "bg-yellow-500/20 text-yellow-400",
  awaiting_approval: "bg-purple-500/20 text-purple-400",
  approved: "bg-green-500/20 text-green-400",
  completed: "bg-green-500/20 text-green-400",
  rejected: "bg-red-500/20 text-red-400",
  failed: "bg-red-500/20 text-red-400",
};

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  awaiting_topic: "Pick a Topic",
  awaiting_hook: "Pick a Hook",
  awaiting_approval: "Review Content",
  approved: "Done",
  completed: "Done",
  rejected: "Rejected",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        STATUS_STYLES[status] || STATUS_STYLES.queued
      }`}
    >
      {STATUS_LABELS[status] || status}
    </span>
  );
}
