"use client";

import Link from "next/link";
import { Deliverable } from "@/lib/api/mission-control";
import { AgentNotification } from "@/lib/api/notifications";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const REJECT_TAGS = ["Wrong voice", "Bad hook", "Needs research", "Off-topic"] as const;
type RejectTag = (typeof REJECT_TAGS)[number];

export function ApprovalInbox({
  deliverables,
  notifications,
  loading,
  expandedIds,
  rejectTarget,
  actionLoading,
  onToggleExpand,
  onApprove,
  onReject,
  onSetRejectTarget,
  onMarkRead,
}: {
  deliverables: Deliverable[];
  notifications: AgentNotification[];
  loading: boolean;
  expandedIds: Set<string>;
  rejectTarget: string | null;
  actionLoading: string | null;
  onToggleExpand: (id: string) => void;
  onApprove: (id: string, content: string) => void;
  onReject: (id: string, tag: RejectTag, content: string) => void;
  onSetRejectTarget: (id: string | null) => void;
  onMarkRead: (id: string) => void;
}) {
  const totalCount = deliverables.length + notifications.length;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
          Needs Your Approval
        </h2>
        {totalCount > 0 && (
          <span className="glass-badge-accent text-[10px]">
            {totalCount}
          </span>
        )}
      </div>

      {loading ? (
        <div className="text-xs text-zinc-500">Loading...</div>
      ) : totalCount === 0 ? (
        <div className="glass-card text-center py-8">
          <p className="text-sm text-zinc-500">All caught up — nothing needs review.</p>
        </div>
      ) : (
        <div className="rounded-2xl ring-1 ring-white/[0.05] overflow-hidden divide-y divide-white/[0.05]">
          {deliverables.map((d) => {
            const isExpanded = expandedIds.has(d.id);
            const preview = (d.content ?? "").slice(0, 120).trim();
            return (
              <div key={d.id} className="bg-white/[0.02] px-5 py-4 space-y-2">
                {/* Title row */}
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm font-medium text-zinc-200 truncate">{d.title}</span>
                    {d.qa_score !== undefined && d.qa_score > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20 font-mono">
                        QA {d.qa_score}
                      </span>
                    )}
                    <span className="text-[10px] text-zinc-600 shrink-0">{timeAgo(d.created_at)}</span>
                  </div>

                  {rejectTarget === d.id ? (
                    <div className="flex flex-wrap gap-1 shrink-0">
                      {REJECT_TAGS.map((tag) => (
                        <button
                          key={tag}
                          onClick={() => onReject(d.id, tag, d.content ?? "")}
                          disabled={actionLoading === d.id}
                          className="px-2 py-1 text-[10px] rounded-lg bg-red-500/10 ring-1 ring-red-500/20 text-red-400 hover:bg-red-500/20 transition-colors"
                        >
                          {tag}
                        </button>
                      ))}
                      <button
                        onClick={() => onSetRejectTarget(null)}
                        className="px-2 py-1 text-[10px] rounded-lg ring-1 ring-white/[0.08] text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Link
                        href={`/composer?id=${d.id}`}
                        className="glass-button text-[11px] px-2 py-1.5"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => onSetRejectTarget(d.id)}
                        disabled={actionLoading === d.id}
                        className="glass-button text-[11px] px-2 py-1.5 hover:ring-red-500/30 hover:text-red-400"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => onApprove(d.id, d.content ?? "")}
                        disabled={actionLoading === d.id}
                        className="text-[11px] px-3 py-1.5 rounded-xl bg-emerald-500/15 ring-1 ring-emerald-500/25 text-emerald-400 hover:bg-emerald-500/25 font-medium transition-colors"
                      >
                        {actionLoading === d.id ? "..." : "Approve"}
                      </button>
                    </div>
                  )}
                </div>

                {/* Content preview / expand */}
                {d.content && (
                  <div className="ml-0">
                    {isExpanded ? (
                      <div className="space-y-2">
                        <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap bg-white/[0.02] ring-1 ring-white/[0.05] rounded-xl px-4 py-3">
                          {d.content}
                        </p>
                        <button
                          onClick={() => onToggleExpand(d.id)}
                          className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
                        >
                          Collapse
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <p className="text-xs text-zinc-500 truncate flex-1">{preview}</p>
                        {(d.content ?? "").length > 120 && (
                          <button
                            onClick={() => onToggleExpand(d.id)}
                            className="text-[10px] text-violet-400 hover:text-violet-300 shrink-0 transition-colors"
                          >
                            Show post
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {notifications.map((n) => (
            <div key={n.id} className="bg-white/[0.02] px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-zinc-200 truncate">{n.title}</span>
                    <span className="text-[10px] text-zinc-600 shrink-0">{timeAgo(n.created_at)}</span>
                  </div>
                  <p className="text-xs text-zinc-500 truncate">{n.body}</p>
                </div>
                <button
                  onClick={() => onMarkRead(n.id)}
                  className="glass-button text-[11px] px-2.5 py-1.5"
                >
                  Dismiss
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
