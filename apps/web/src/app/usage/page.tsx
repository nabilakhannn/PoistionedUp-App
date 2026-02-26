"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import {
  usageApi,
  UsageSummary,
  DailyUsage,
} from "@/lib/api";

function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toString();
}

function CapGauge({
  label,
  used,
  cap,
  unit,
}: {
  label: string;
  used: number;
  cap: number;
  unit: string;
}) {
  const percent = cap > 0 ? Math.round((used / cap) * 100) : 0;
  const barColor =
    percent >= 100
      ? "bg-red-500"
      : percent >= 80
      ? "bg-yellow-500"
      : "bg-emerald-500";

  return (
    <div className="bg-card border border-border rounded-lg p-5">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
        {label}
      </h3>
      <div className="flex items-end gap-2 mb-2">
        <span className="text-2xl font-bold text-foreground">
          {unit === "tokens" ? formatTokens(used) : used}
        </span>
        <span className="text-muted-foreground text-sm mb-0.5">
          / {unit === "tokens" ? formatTokens(cap) : cap} {unit} today
        </span>
      </div>
      <div className="w-full bg-accent rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        {cap - used > 0
          ? `${unit === "tokens" ? formatTokens(cap - used) : cap - used} remaining`
          : "Limit reached. Resets at midnight UTC."}
      </p>
    </div>
  );
}

export default function UsagePage() {
  const { brandId, loading: brandLoading } = useBrand();
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [daily, setDaily] = useState<DailyUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (brandLoading) return;
    async function load() {
      try {
        const [s, d] = await Promise.all([
          usageApi.getSummary(brandId || undefined),
          usageApi.getDaily(30, brandId || undefined),
        ]);
        setSummary(s);
        setDaily(d);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [brandId, brandLoading]);

  if (loading) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-accent rounded w-48" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-accent/60 rounded-lg" />
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="h-40 bg-accent/60 rounded-lg" />
            <div className="h-40 bg-accent/60 rounded-lg" />
          </div>
          <div className="h-48 bg-accent/60 rounded-lg" />
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-10">
        <p className="text-red-400">Error loading usage data: {error}</p>
      </main>
    );
  }

  if (!summary) return null;

  const wfCapPercent = summary.daily_workflow_cap
    ? Math.round(
        (summary.daily_workflows_used / summary.daily_workflow_cap) * 100
      )
    : 0;

  const tokenCapPercent = summary.daily_token_cap
    ? Math.round(
        (summary.daily_tokens_used / summary.daily_token_cap) * 100
      )
    : 0;

  // Find max cost for the bar chart scaling
  const maxDailyCost = Math.max(...daily.map((d) => d.total_cost), 0.001);

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Usage & Costs</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Track your AI usage, token consumption, and spending
          </p>
        </div>
        <Link
          href="/content"
          className="text-sm text-primary hover:text-primary"
        >
          Back to Content
        </Link>
      </div>

      {/* Cap warnings */}
      {(wfCapPercent >= 80 || tokenCapPercent >= 80) && (
        <div
          className={`p-4 rounded-lg mb-6 border ${
            wfCapPercent >= 100 || tokenCapPercent >= 100
              ? "bg-red-500/10 border-red-500/30"
              : "bg-yellow-500/10 border-yellow-500/30"
          }`}
        >
          <p
            className={`text-sm font-medium ${
              wfCapPercent >= 100 || tokenCapPercent >= 100
                ? "text-red-400"
                : "text-yellow-400"
            }`}
          >
            {wfCapPercent >= 100
              ? `Daily workflow limit reached (${summary.daily_workflows_used}/${summary.daily_workflow_cap}). Resets at midnight UTC.`
              : tokenCapPercent >= 100
              ? `Daily token limit reached (${formatTokens(summary.daily_tokens_used)}/${formatTokens(summary.daily_token_cap)}). Resets at midnight UTC.`
              : wfCapPercent >= 80
              ? `Approaching daily workflow limit: ${summary.daily_workflows_used} of ${summary.daily_workflow_cap} used.`
              : `Approaching daily token limit: ${formatTokens(summary.daily_tokens_used)} of ${formatTokens(summary.daily_token_cap)} used.`}
          </p>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-card border border-border rounded-lg p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">
            Total Spent
          </p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {formatCost(summary.total_cost)}
          </p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">
            Today
          </p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {formatCost(summary.period_costs.daily)}
          </p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">
            This Week
          </p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {formatCost(summary.period_costs.weekly)}
          </p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">
            This Month
          </p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {formatCost(summary.period_costs.monthly)}
          </p>
        </div>
      </div>

      {/* Token usage + Cap gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-card border border-border rounded-lg p-5">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
            Token Usage
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Input tokens</span>
              <span className="font-medium text-foreground">
                {formatTokens(summary.total_input_tokens)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Output tokens</span>
              <span className="font-medium text-foreground">
                {formatTokens(summary.total_output_tokens)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Total LLM calls</span>
              <span className="font-medium text-foreground">{summary.total_calls}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Workflows</span>
              <span className="font-medium text-foreground">{summary.workflow_count}</span>
            </div>
          </div>
        </div>

        <CapGauge
          label="Daily Workflow Cap"
          used={summary.daily_workflows_used}
          cap={summary.daily_workflow_cap}
          unit="workflows"
        />

        <CapGauge
          label="Daily Token Cap"
          used={summary.daily_tokens_used}
          cap={summary.daily_token_cap}
          unit="tokens"
        />
      </div>

      {/* Daily cost chart (simple bar chart) */}
      <div className="bg-card border border-border rounded-lg p-6 mb-8">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">
          Daily Spending (Last 30 Days)
        </h3>
        <div className="flex items-end gap-[2px] h-32">
          {daily.map((d) => {
            const height = Math.max(
              (d.total_cost / maxDailyCost) * 100,
              d.total_cost > 0 ? 4 : 0
            );
            return (
              <div
                key={d.date}
                className="flex-1 group relative"
                title={`${d.date}: ${formatCost(d.total_cost)} (${d.call_count} calls)`}
              >
                <div
                  className="bg-primary/70 hover:bg-primary rounded-t transition-colors w-full"
                  style={{ height: `${height}%` }}
                />
                {/* Tooltip on hover */}
                <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1 bg-muted text-foreground text-xs rounded px-2 py-1 whitespace-nowrap z-10">
                  {d.date}: {formatCost(d.total_cost)}
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-xs text-muted-foreground">
            {daily.length > 0 ? daily[0].date : ""}
          </span>
          <span className="text-xs text-muted-foreground">
            {daily.length > 0 ? daily[daily.length - 1].date : ""}
          </span>
        </div>
      </div>

      {/* Per-workflow breakdown */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">
          Cost by Workflow
        </h3>
        {summary.workflows.length === 0 ? (
          <p className="text-muted-foreground text-sm text-center py-8">
            No usage data yet. Create your first content workflow to start
            tracking costs.
          </p>
        ) : (
          <div className="space-y-2">
            {summary.workflows.map((wf) => (
              <Link
                key={wf.workflow_id}
                href={`/content/${wf.workflow_id}`}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-accent/50 transition border border-border/50"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground truncate">
                    {wf.goal_text}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {wf.step_count} LLM calls &middot;{" "}
                    {formatTokens(
                      wf.total_input_tokens + wf.total_output_tokens
                    )}{" "}
                    tokens
                  </p>
                </div>
                <span className="text-sm font-medium text-foreground ml-4">
                  {formatCost(wf.total_cost)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
