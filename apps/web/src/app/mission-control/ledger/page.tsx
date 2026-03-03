"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ledgerApi, AgentRun, LedgerEntry, LedgerSummary } from "@/lib/api/ledger";
import { MC_SUB_NAV } from "../constants";

const STATUS_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  completed: { label: "Completed", color: "text-green-400", bg: "bg-green-500/20" },
  running: { label: "Running", color: "text-blue-400", bg: "bg-blue-500/20" },
  failed: { label: "Failed", color: "text-red-400", bg: "bg-red-500/20" },
};

const ACTION_ICONS: Record<string, string> = {
  tool_call: "🔧",
  decision: "💭",
  output: "📤",
  error: "❌",
};

function fmt(ms: number | null) {
  if (!ms) return "—";
  return ms > 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function fmtTokens(n: number) {
  return n > 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

export default function LedgerPage() {
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [entries, setEntries] = useState<Record<string, LedgerEntry[]>>({});
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [loadingEntries, setLoadingEntries] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [summaryData, runsData] = await Promise.all([
        ledgerApi.getSummary(7),
        ledgerApi.listRuns({ limit: 50, status: statusFilter }),
      ]);
      setSummary(summaryData);
      setRuns(runsData);
    } catch (e) {
      console.error("Failed to load ledger data:", e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const toggleRun = async (runId: string) => {
    if (expandedRun === runId) {
      setExpandedRun(null);
      return;
    }
    setExpandedRun(runId);
    if (!entries[runId]) {
      setLoadingEntries(runId);
      try {
        const data = await ledgerApi.getRunEntries(runId);
        setEntries(prev => ({ ...prev, [runId]: data }));
      } catch {
        console.error("Failed to load entries for run", runId);
      } finally {
        setLoadingEntries(null);
      }
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Sub-nav */}
      <div className="flex items-center gap-1 flex-wrap">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control/ledger"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Agent Ledger</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Immutable audit trail — every tool call, decision, and output your agents made.
        </p>
      </div>

      {/* Summary bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Runs (7d)", value: summary.total_runs },
            { label: "Completed", value: summary.completed },
            { label: "Avg Tokens", value: fmtTokens(summary.avg_tokens_per_run) },
            { label: "Tool Calls", value: summary.total_tool_calls },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">{label}</div>
              <div className="text-xl font-semibold mt-1">{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2">
        {[
          { key: undefined, label: "All" },
          { key: "completed", label: "Completed" },
          { key: "failed", label: "Failed" },
          { key: "running", label: "Running" },
        ].map(({ key, label }) => (
          <button
            key={label}
            onClick={() => setStatusFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              statusFilter === key
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Runs table */}
      {loading ? (
        <div className="text-muted-foreground text-sm">Loading runs...</div>
      ) : runs.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground text-sm">
          No agent runs yet. Runs appear here once an agent uses the tool-use loop.
        </div>
      ) : (
        <div className="space-y-2">
          {runs.map((run) => {
            const st = STATUS_STYLES[run.status] || STATUS_STYLES.failed;
            return (
              <div key={run.id} className="rounded-lg border border-border bg-card overflow-hidden">
                {/* Run row */}
                <button
                  className="w-full px-4 py-3 flex items-center gap-4 hover:bg-accent/50 transition text-left"
                  onClick={() => toggleRun(run.id)}
                >
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${st.bg} ${st.color}`}>{st.label}</span>
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-sm">{run.agent_id}</span>
                    <span className="text-muted-foreground text-xs ml-2">{run.task_type}</span>
                    {run.prompt_summary && (
                      <span className="text-muted-foreground text-xs ml-2 truncate hidden sm:inline">
                        — {run.prompt_summary}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
                    <span>🔧 {run.tool_calls_count}</span>
                    <span>⚡ {fmtTokens(run.total_tokens)}</span>
                    <span>⏱ {fmt(run.duration_ms)}</span>
                    <span>{new Date(run.created_at).toLocaleTimeString()}</span>
                    <span className="text-muted-foreground">{expandedRun === run.id ? "▲" : "▼"}</span>
                  </div>
                </button>

                {/* Expanded entries */}
                {expandedRun === run.id && (
                  <div className="border-t border-border px-4 py-3 space-y-2">
                    {loadingEntries === run.id ? (
                      <div className="text-xs text-muted-foreground">Loading entries...</div>
                    ) : (entries[run.id] || []).length === 0 ? (
                      <div className="text-xs text-muted-foreground">No entries recorded for this run.</div>
                    ) : (
                      (entries[run.id] || []).map((entry) => (
                        <div key={entry.id} className="flex gap-3 text-xs">
                          <span className="shrink-0 w-5">{ACTION_ICONS[entry.action_type] || "•"}</span>
                          <div className="flex-1 space-y-0.5">
                            <div className="text-foreground">{entry.action_description}</div>
                            {entry.tool_input_summary && (
                              <div className="text-muted-foreground">In: {entry.tool_input_summary}</div>
                            )}
                            {entry.tool_result_summary && (
                              <div className="text-muted-foreground">Out: {entry.tool_result_summary}</div>
                            )}
                          </div>
                          <span className="text-muted-foreground shrink-0">
                            {new Date(entry.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
