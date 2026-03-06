"use client";

/**
 * Client Detail Page — Slice 111
 * Drill-down view for a single client brand: info, sessions, action items, deliverables.
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api/client";
import {
  accountManagerApi,
  type AccountManagerSession,
  type ActionItem,
} from "@/lib/api/account-manager";
import {
  clientDeliverablesApi,
  type ClientDeliverable,
  type ProposalStatus,
} from "@/lib/api/client-deliverables";

interface ClientBrand {
  id: string;
  name: string;
  niche?: string;
  created_at: string;
  profile_json?: Record<string, unknown>;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-700/30 text-slate-400",
  sent: "bg-blue-500/10 text-blue-400",
  accepted: "bg-green-500/10 text-green-400",
  rejected: "bg-red-500/10 text-red-400",
  closed_won: "bg-emerald-500/10 text-emerald-400",
  closed_lost: "bg-zinc-500/10 text-zinc-500",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export default function ClientDetailPage() {
  const params = useParams();
  const brandId = params.brandId as string;

  const [brand, setBrand] = useState<ClientBrand | null>(null);
  const [sessions, setSessions] = useState<AccountManagerSession[]>([]);
  const [deliverables, setDeliverables] = useState<ClientDeliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [savingAction, setSavingAction] = useState(false);

  const load = useCallback(async () => {
    if (!brandId) return;
    setLoading(true);
    setError("");
    try {
      const [brandData, sessionsData, deliverablesData] = await Promise.all([
        apiFetch<ClientBrand>(`/brands/${brandId}`),
        accountManagerApi.listSessions(brandId),
        clientDeliverablesApi.list(brandId),
      ]);
      setBrand(brandData);
      setSessions(sessionsData);
      setDeliverables(deliverablesData);
    } catch {
      setError("Failed to load client details");
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleToggleExecuted(
    session: AccountManagerSession,
    actionId: string,
  ) {
    setSavingAction(true);
    const updated = session.action_plan.map((a) =>
      a.id === actionId ? { ...a, executed: !a.executed } : a,
    );
    try {
      await accountManagerApi.updateSession(session.id, updated);
      setSessions((prev) =>
        prev.map((s) =>
          s.id === session.id ? { ...s, action_plan: updated } : s,
        ),
      );
    } catch {
      // silent
    } finally {
      setSavingAction(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
          <div className="h-5 w-48 rounded bg-zinc-800/50 animate-pulse" />
          <div className="h-3 w-32 rounded bg-zinc-800/40 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.03] p-5 animate-pulse"
              >
                <div className="h-4 w-32 rounded bg-zinc-800/50 mb-3" />
                <div className="h-3 w-full rounded bg-zinc-800/40" />
                <div className="h-3 w-2/3 rounded bg-zinc-800/40 mt-2" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-red-400 mb-3">{error}</p>
          <button onClick={load} className="glass-button-primary text-sm">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const allActions = sessions.flatMap((s) =>
    s.action_plan.map((a) => ({ ...a, sessionId: s.id, callNumber: s.call_number })),
  );
  const pendingActions = allActions.filter((a) => !a.executed);

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <Link href="/mission-control/clients" className="hover:text-zinc-300 transition-colors">
            Clients
          </Link>
          <span>/</span>
          <span className="text-zinc-300">{brand?.name || brandId.slice(0, 8)}</span>
        </div>

        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-zinc-100">
            {brand?.name || "Client"}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            {brand?.niche && (
              <span className="text-xs text-zinc-500">{brand.niche}</span>
            )}
            {brand?.created_at && (
              <span className="text-xs text-zinc-600">
                Client since {new Date(brand.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
              </span>
            )}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="glass-card p-4 text-center">
            <div className="text-2xl font-bold text-zinc-100">{sessions.length}</div>
            <div className="text-xs text-zinc-500 mt-0.5">Calls</div>
          </div>
          <div className="glass-card p-4 text-center">
            <div className="text-2xl font-bold text-zinc-100">{pendingActions.length}</div>
            <div className="text-xs text-zinc-500 mt-0.5">Pending Actions</div>
          </div>
          <div className="glass-card p-4 text-center">
            <div className="text-2xl font-bold text-zinc-100">{deliverables.length}</div>
            <div className="text-xs text-zinc-500 mt-0.5">Deliverables</div>
          </div>
        </div>

        {/* Session History */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-zinc-300">Session History</h2>
          {sessions.length === 0 ? (
            <div className="glass-card text-center py-8">
              <p className="text-zinc-400 text-sm">No sessions yet.</p>
              <p className="text-zinc-600 text-xs mt-1">Analyze a client call to create the first session.</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div key={session.id} className="glass-card">
                <button
                  className="w-full text-left flex items-center justify-between gap-3"
                  onClick={() =>
                    setExpandedSession(
                      expandedSession === session.id ? null : session.id,
                    )
                  }
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-zinc-200">
                        Call #{session.call_number}
                      </span>
                      <span className="text-xs text-zinc-600">
                        {new Date(session.call_date).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400 line-clamp-1">{session.summary}</p>
                    {session.cross_call_themes.length > 0 && (
                      <div className="flex gap-1 flex-wrap mt-1">
                        {session.cross_call_themes.slice(0, 4).map((t) => (
                          <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="text-zinc-500 text-xs shrink-0">
                    {expandedSession === session.id ? "▲" : "▼"}
                  </span>
                </button>

                {/* Expanded: action plan */}
                {expandedSession === session.id && (
                  <div className="mt-3 pt-3 border-t border-zinc-800 space-y-2">
                    <p className="text-xs text-zinc-500 font-medium">
                      Action Plan ({session.action_plan.length} items)
                    </p>
                    {session.action_plan.map((action) => (
                      <div
                        key={action.id}
                        className="flex items-start gap-2 rounded-lg bg-zinc-900/50 p-3"
                      >
                        <button
                          onClick={() => handleToggleExecuted(session, action.id)}
                          disabled={savingAction}
                          className={`mt-0.5 w-4 h-4 rounded border shrink-0 flex items-center justify-center transition-colors ${
                            action.executed
                              ? "bg-green-500/20 border-green-500/50 text-green-400"
                              : "border-zinc-600 hover:border-zinc-400"
                          }`}
                        >
                          {action.executed && (
                            <span className="text-[10px]">✓</span>
                          )}
                        </button>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-sm ${
                                action.executed
                                  ? "text-zinc-500 line-through"
                                  : "text-zinc-200"
                              }`}
                            >
                              {action.title}
                            </span>
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded ${
                                action.priority === "high"
                                  ? "bg-red-500/10 text-red-400"
                                  : action.priority === "medium"
                                    ? "bg-amber-500/10 text-amber-400"
                                    : "bg-zinc-700/50 text-zinc-500"
                              }`}
                            >
                              {action.priority}
                            </span>
                          </div>
                          <p className="text-xs text-zinc-500 mt-0.5">
                            {action.description}
                          </p>
                          {action.result && (
                            <p className="text-xs text-green-400/80 mt-1">
                              Result: {action.result}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Deliverables */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-zinc-300">Deliverables</h2>
          {deliverables.length === 0 ? (
            <div className="glass-card text-center py-8">
              <p className="text-zinc-400 text-sm">No deliverables yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {deliverables.map((d) => (
                <div key={d.id} className="glass-card p-4 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-zinc-200 truncate">
                      {d.title}
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {d.proposal_status && (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                            STATUS_COLORS[d.proposal_status] || STATUS_COLORS.draft
                          }`}
                        >
                          {d.proposal_status.replace("_", " ")}
                        </span>
                      )}
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-900/30 text-indigo-400">
                        v{d.version}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-zinc-500">{timeAgo(d.created_at)}</p>
                  <div className="flex gap-2">
                    <Link
                      href={`/share/${d.share_token}`}
                      target="_blank"
                      className="glass-button text-xs px-2 py-1"
                    >
                      Preview
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
