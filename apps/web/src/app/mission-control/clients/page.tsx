"use client";

/**
 * Client Health Dashboard — Slice 98
 * All client brands at a glance — posts, last call, next action, status.
 */

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api/client";
import { accountManagerApi, type AccountManagerSession } from "@/lib/api/account-manager";
import { MC_SUB_NAV } from "../constants";

interface ClientBrand {
  id: string;
  name: string;
  niche?: string;
  is_client_brand: boolean;
  created_at: string;
  profile_json?: { positioning?: string; ica_summary?: string };
}

interface ClientRow {
  brand: ClientBrand;
  latestSession: AccountManagerSession | null;
  postsThisMonth: number;
  status: "active" | "pending_intake" | "needs_call" | "new";
  nextAction: string;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const STATUS_CONFIG = {
  active: { label: "Active", dot: "bg-green-400", text: "text-green-400" },
  pending_intake: { label: "Pending Intake", dot: "bg-yellow-400", text: "text-yellow-400" },
  needs_call: { label: "Needs Call", dot: "bg-orange-400", text: "text-orange-400" },
  new: { label: "New", dot: "bg-slate-400", text: "text-slate-400" },
};

function buildNextAction(row: Omit<ClientRow, "nextAction">): string {
  if (!row.latestSession) return "Run Brand Research";
  const pendingCount = row.latestSession.action_plan.filter((a) => a.approved === null).length;
  if (pendingCount > 0) return `Review ${pendingCount} action${pendingCount === 1 ? "" : "s"}`;
  const unapprovedExecutable = row.latestSession.action_plan.filter(
    (a) => a.approved === true && !a.executed
  ).length;
  if (unapprovedExecutable > 0) return `Execute ${unapprovedExecutable} approved item${unapprovedExecutable === 1 ? "" : "s"}`;
  return "Schedule next call";
}

function buildStatus(brand: ClientBrand, session: AccountManagerSession | null): ClientRow["status"] {
  if (!session) return "new";
  const daysSinceCall = (Date.now() - new Date(session.call_date || session.created_at).getTime()) / 86400000;
  if (daysSinceCall > 21) return "needs_call";
  const pendingApproval = session.action_plan.filter((a) => a.approved === null).length;
  if (pendingApproval > 0) return "active";
  return "active";
}

export default function ClientsPage() {
  const [rows, setRows] = useState<ClientRow[]>([]);
  const [loading, setLoading] = useState(true);

  const loadClients = useCallback(async () => {
    try {
      // Load all client brands
      const brands = await apiFetch<ClientBrand[]>("/brands?is_client=true").catch(() => [] as ClientBrand[]);
      const clientBrands = brands.filter((b) => b.is_client_brand);

      // For each brand, load their latest session + post count in parallel
      const rowsData = await Promise.all(
        clientBrands.map(async (brand) => {
          const [sessions, postsRes] = await Promise.all([
            accountManagerApi.listSessions(brand.id).catch(() => [] as AccountManagerSession[]),
            apiFetch<{ count: number }>(`/brands/${brand.id}/stats?period=month`).catch(() => ({ count: 0 })),
          ]);

          const latestSession = sessions.length > 0 ? sessions[0] : null;
          const status = buildStatus(brand, latestSession);
          const row: Omit<ClientRow, "nextAction"> = { brand, latestSession, postsThisMonth: postsRes.count ?? 0, status };
          return { ...row, nextAction: buildNextAction(row) };
        })
      );

      setRows(rowsData);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadClients();
  }, [loadClients]);

  return (
    <div className="min-h-screen bg-background">
      {/* Sub-nav */}
      <div className="h-12 border-b border-border bg-card/50 flex items-center px-5 gap-1">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control/clients"
                ? "bg-primary/15 text-primary border border-primary/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      <div className="max-w-5xl mx-auto px-5 py-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground">Clients</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              All client brands — health, activity, next actions
            </p>
          </div>
          <Link
            href="/onboarding/client"
            className="px-4 py-2 rounded-xl text-sm font-semibold text-white"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
          >
            + Add Client
          </Link>
        </div>

        {loading ? (
          <div className="text-muted-foreground text-sm py-10 text-center">Loading clients...</div>
        ) : rows.length === 0 ? (
          <div className="rounded-2xl border border-border bg-card p-12 text-center">
            <div className="text-4xl mb-3">👥</div>
            <p className="text-foreground font-medium">No clients yet</p>
            <p className="text-muted-foreground text-xs mt-1 mb-5">
              Add your first client to start building their content intelligence dossier.
            </p>
            <Link
              href="/onboarding/client"
              className="inline-block px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
            >
              Add First Client
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[2fr_1fr_1fr_1.5fr_1fr] gap-4 px-5 py-3 border-b border-border">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Client</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Posts / Mo</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Last Call</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Next Action</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Status</div>
            </div>

            {/* Rows */}
            <div className="divide-y divide-border">
              {rows.map(({ brand, latestSession, postsThisMonth, status, nextAction }) => {
                const statusCfg = STATUS_CONFIG[status];
                return (
                  <div
                    key={brand.id}
                    className="grid grid-cols-[2fr_1fr_1fr_1.5fr_1fr] gap-4 px-5 py-4 items-center hover:bg-accent/30 transition-colors"
                  >
                    {/* Client name */}
                    <div>
                      <div className="text-sm font-semibold text-foreground">{brand.name}</div>
                      {brand.niche && (
                        <div className="text-xs text-muted-foreground truncate max-w-[180px]">
                          {brand.niche}
                        </div>
                      )}
                      {latestSession && (
                        <div className="text-[10px] text-muted-foreground/60 mt-0.5">
                          Call #{latestSession.call_number}
                        </div>
                      )}
                    </div>

                    {/* Posts */}
                    <div>
                      <span className="text-sm font-bold text-foreground">{postsThisMonth}</span>
                      <span className="text-xs text-muted-foreground ml-1">posts</span>
                    </div>

                    {/* Last call */}
                    <div className="text-xs text-muted-foreground">
                      {latestSession
                        ? timeAgo(latestSession.call_date || latestSession.created_at)
                        : "—"}
                    </div>

                    {/* Next action */}
                    <div>
                      <Link
                        href={
                          nextAction === "Run Brand Research"
                            ? `/onboarding/client?brand_id=${brand.id}`
                            : latestSession
                            ? `/mission-control?session=${latestSession.id}`
                            : "/mission-control"
                        }
                        className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        {nextAction} →
                      </Link>
                    </div>

                    {/* Status */}
                    <div className="flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${statusCfg.dot}`} />
                      <span className={`text-xs font-medium ${statusCfg.text}`}>
                        {statusCfg.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Recent call summaries */}
        {rows.length > 0 && rows.some((r) => r.latestSession) && (
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
              Recent Call Summaries
            </h2>
            <div className="space-y-2">
              {rows
                .filter((r) => r.latestSession)
                .slice(0, 5)
                .map(({ brand, latestSession }) => (
                  <div
                    key={latestSession!.id}
                    className="rounded-xl border border-border bg-card px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-foreground">
                            {brand.name}
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            Call #{latestSession!.call_number} ·{" "}
                            {timeAgo(latestSession!.call_date || latestSession!.created_at)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                          {latestSession!.summary}
                        </p>
                        {latestSession!.cross_call_themes?.length > 0 && (
                          <div className="flex gap-1 flex-wrap mt-1.5">
                            {latestSession!.cross_call_themes.slice(0, 3).map((theme) => (
                              <span
                                key={theme}
                                className="px-2 py-0.5 bg-yellow-900/20 text-yellow-500 border border-yellow-800/30 rounded-full text-[10px]"
                              >
                                {theme}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <Link
                        href={`/mission-control?session=${latestSession!.id}`}
                        className="shrink-0 px-3 py-1.5 border border-border text-muted-foreground hover:text-foreground text-xs rounded-lg transition-colors"
                      >
                        View Plan →
                      </Link>
                    </div>
                  </div>
                ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
