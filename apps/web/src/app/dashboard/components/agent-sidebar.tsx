"use client";

import Link from "next/link";

interface ActivityItem {
  id: string;
  agent_id: string;
  task_type: string;
  summary: string;
  status: string;
  created_at: string;
  brand_id: string | null;
  emoji: string;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function AgentActivity({ overnight }: { overnight: ActivityItem[] }) {
  const grouped = overnight.reduce<Record<string, ActivityItem[]>>((acc, item) => {
    const key = item.agent_id ?? "unknown";
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  return (
    <section>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">
        Agent Activity
      </h2>
      <div className="glass-card">
        {overnight.length === 0 ? (
          <p className="text-xs text-zinc-600">
            No activity yet today · Pipeline runs every 2h
          </p>
        ) : (
          <div className="space-y-2">
            {Object.entries(grouped).map(([agentId, items]) => {
              const successCount = items.filter((i) => i.status === "success" || i.status === "completed").length;
              const failCount = items.filter((i) => i.status === "failed" || i.status === "error").length;
              const latest = items[0];
              return (
                <div key={agentId} className="flex items-start gap-2.5">
                  <span className="text-sm shrink-0">{latest.emoji ?? "·"}</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-medium text-zinc-300 capitalize">{agentId.replace(/-/g, " ")}</span>
                    <span className="text-xs text-zinc-600 ml-1.5">
                      {items.length} task{items.length !== 1 ? "s" : ""}
                      {successCount > 0 && <span className="text-emerald-400 ml-1">· {successCount} done</span>}
                      {failCount > 0 && <span className="text-red-400 ml-1">· {failCount} failed</span>}
                      <span className="ml-1 text-zinc-700">· {timeAgo(latest.created_at)}</span>
                    </span>
                    {latest.summary && (
                      <p className="text-[10px] text-zinc-600 truncate mt-0.5">{latest.summary}</p>
                    )}
                  </div>
                </div>
              );
            })}
            <div className="pt-2 border-t border-white/[0.04]">
              <Link href="/brand?tab=team" className="text-[10px] text-violet-400 hover:text-violet-300 transition-colors">
                View full activity log →
              </Link>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
