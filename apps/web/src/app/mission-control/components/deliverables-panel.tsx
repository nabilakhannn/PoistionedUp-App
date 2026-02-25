"use client";

import { useState } from "react";
import { Deliverable, Agent, missionControlApi } from "@/lib/api/mission-control";

interface DeliverablesPanelProps {
  deliverables: Deliverable[];
  agents: Agent[];
  onUpdate: () => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  draft: { bg: "bg-zinc-500/20", text: "text-zinc-400", label: "DRAFT" },
  review: { bg: "bg-amber-500/20", text: "text-amber-400", label: "REVIEW" },
  approved: { bg: "bg-green-500/20", text: "text-green-400", label: "APPROVED" },
  rejected: { bg: "bg-red-500/20", text: "text-red-400", label: "REJECTED" },
};

const TYPE_ICONS: Record<string, string> = {
  document: "📄",
  image: "🖼️",
  code: "💻",
  report: "📊",
  content: "✍️",
};

export function DeliverablesPanel({ deliverables, agents, onUpdate }: DeliverablesPanelProps) {
  const [filter, setFilter] = useState<"all" | "review" | "approved" | "rejected">("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [feedbackInput, setFeedbackInput] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const agentMap = new Map(agents.map((a) => [a.id, a]));

  const filtered = filter === "all"
    ? deliverables
    : deliverables.filter((d) => d.status === filter);

  const reviewCount = deliverables.filter((d) => d.status === "review").length;

  const handleAction = async (id: string, status: "approved" | "rejected") => {
    setActionLoading(id);
    try {
      const feedback = status === "rejected" ? feedbackInput.trim() : undefined;
      await missionControlApi.updateDeliverable(id, status, feedback);
      setFeedbackInput("");
      setExpandedId(null);
      onUpdate();
    } catch (err) {
      console.error("Deliverable action error:", err);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
          <span>📦</span>
          Deliverables
          {reviewCount > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-[10px] font-bold animate-pulse">
              {reviewCount} to review
            </span>
          )}
        </h3>

        {/* Filter tabs */}
        <div className="flex gap-1">
          {(["all", "review", "approved", "rejected"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                filter === f
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-zinc-600 hover:text-zinc-400"
              }`}
            >
              {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Deliverables list */}
      <div className="max-h-96 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-zinc-600">
              {filter === "review" ? "No deliverables awaiting review" : "No deliverables yet"}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {filtered.map((d) => {
              const creator = d.created_by_agent_id ? agentMap.get(d.created_by_agent_id) : null;
              const statusStyle = STATUS_STYLES[d.status] || STATUS_STYLES.draft;
              const typeIcon = TYPE_ICONS[d.deliverable_type] || "📄";
              const isExpanded = expandedId === d.id;

              return (
                <div key={d.id} className="px-5 py-3">
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : d.id)}
                    className="w-full text-left"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-2 min-w-0 flex-1">
                        <span className="text-lg flex-shrink-0">{typeIcon}</span>
                        <div className="min-w-0">
                          <h4 className="text-sm font-medium text-zinc-200 truncate">
                            {d.title}
                          </h4>
                          <div className="flex items-center gap-2 mt-0.5">
                            {creator && (
                              <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                                {creator.avatar_emoji} {creator.name}
                              </span>
                            )}
                            <span className="text-[10px] text-zinc-600">
                              {timeAgo(d.created_at)}
                            </span>
                            {d.task_id && (
                              <span className="text-[10px] font-mono text-zinc-600 bg-zinc-800 px-1 rounded">
                                {d.task_id}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded ${statusStyle.bg} ${statusStyle.text} flex-shrink-0`}>
                        {statusStyle.label}
                      </span>
                    </div>
                  </button>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="mt-3 ml-8">
                      {/* Content preview */}
                      {d.content && (
                        <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-3 mb-3 max-h-48 overflow-y-auto">
                          <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-sans leading-relaxed">
                            {d.content}
                          </pre>
                        </div>
                      )}

                      {/* File path */}
                      {d.file_path && (
                        <div className="text-[11px] text-zinc-500 mb-3 flex items-center gap-1.5">
                          <span>📁</span>
                          <code className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400">{d.file_path}</code>
                        </div>
                      )}

                      {/* Previous feedback */}
                      {d.feedback && (
                        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2.5 mb-3">
                          <p className="text-[10px] text-red-400 uppercase tracking-wider mb-1 font-bold">Previous Feedback</p>
                          <p className="text-xs text-zinc-300">{d.feedback}</p>
                        </div>
                      )}

                      {/* Actions */}
                      {d.status === "review" && (
                        <div className="space-y-2">
                          <textarea
                            value={feedbackInput}
                            onChange={(e) => setFeedbackInput(e.target.value)}
                            placeholder="Optional feedback (required for rejection)..."
                            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-500 resize-none h-16"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleAction(d.id, "approved")}
                              disabled={actionLoading === d.id}
                              className="flex-1 px-3 py-2 rounded-lg bg-green-600 text-white text-xs font-bold hover:bg-green-500 disabled:opacity-40 transition flex items-center justify-center gap-1.5"
                            >
                              <span>✓</span> Approve
                            </button>
                            <button
                              onClick={() => handleAction(d.id, "rejected")}
                              disabled={actionLoading === d.id || !feedbackInput.trim()}
                              className="flex-1 px-3 py-2 rounded-lg bg-red-600/80 text-white text-xs font-bold hover:bg-red-500 disabled:opacity-40 transition flex items-center justify-center gap-1.5"
                            >
                              <span>✗</span> Reject
                            </button>
                          </div>
                        </div>
                      )}

                      {d.status === "approved" && (
                        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20">
                          <span className="text-green-400">✓</span>
                          <span className="text-xs text-green-400 font-medium">Approved</span>
                        </div>
                      )}

                      {d.status === "rejected" && (
                        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
                          <span className="text-red-400">✗</span>
                          <span className="text-xs text-red-400 font-medium">Rejected — awaiting revision</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
