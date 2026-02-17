"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface WorkflowCost {
  workflow_id: string;
  goal_text: string;
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  step_count: number;
  created_at: string | null;
}

interface UsageSummary {
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_calls: number;
  workflow_count: number;
  daily_workflows_used: number;
  daily_workflow_cap: number;
  period_costs: {
    daily: number;
    weekly: number;
    monthly: number;
  };
  workflows: WorkflowCost[];
}

interface DailyUsage {
  date: string;
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  call_count: number;
}

// Simple API fetch with auth
async function fetchUsage<T>(path: string): Promise<T> {
  const { createClient } = await import("@/lib/supabase/client");
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token ?? "";

  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch usage data");
  return res.json();
}

function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toString();
}

export default function UsagePage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [daily, setDaily] = useState<DailyUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [s, d] = await Promise.all([
          fetchUsage<UsageSummary>("/usage"),
          fetchUsage<DailyUsage[]>("/usage/daily?days=30"),
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
  }, []);

  if (loading) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-10">
        <p className="text-red-600">Error loading usage data: {error}</p>
      </main>
    );
  }

  if (!summary) return null;

  const capPercent = summary.daily_workflow_cap
    ? Math.round(
        (summary.daily_workflows_used / summary.daily_workflow_cap) * 100
      )
    : 0;

  // Find max cost for the bar chart scaling
  const maxDailyCost = Math.max(...daily.map((d) => d.total_cost), 0.001);

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usage & Costs</h1>
          <p className="text-gray-500 text-sm mt-1">
            Track your AI usage, token consumption, and spending
          </p>
        </div>
        <Link
          href="/content"
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Back to Content
        </Link>
      </div>

      {/* Daily cap warning */}
      {capPercent >= 80 && (
        <div
          className={`p-4 rounded-lg mb-6 ${
            capPercent >= 100
              ? "bg-red-50 border border-red-200"
              : "bg-yellow-50 border border-yellow-200"
          }`}
        >
          <p
            className={`text-sm font-medium ${
              capPercent >= 100 ? "text-red-800" : "text-yellow-800"
            }`}
          >
            {capPercent >= 100
              ? `Daily workflow limit reached (${summary.daily_workflows_used}/${summary.daily_workflow_cap}). New workflows will be available tomorrow.`
              : `Approaching daily limit: ${summary.daily_workflows_used} of ${summary.daily_workflow_cap} workflows used today.`}
          </p>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">
            Total Spent
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {formatCost(summary.total_cost)}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">
            Today
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {formatCost(summary.period_costs.daily)}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">
            This Week
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {formatCost(summary.period_costs.weekly)}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">
            This Month
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {formatCost(summary.period_costs.monthly)}
          </p>
        </div>
      </div>

      {/* Token usage + Cap gauge */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            Token Usage
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-500 text-sm">Input tokens</span>
              <span className="font-medium">
                {formatTokens(summary.total_input_tokens)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 text-sm">Output tokens</span>
              <span className="font-medium">
                {formatTokens(summary.total_output_tokens)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 text-sm">Total LLM calls</span>
              <span className="font-medium">{summary.total_calls}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 text-sm">Workflows created</span>
              <span className="font-medium">{summary.workflow_count}</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            Daily Workflow Cap
          </h3>
          <div className="flex items-end gap-2 mb-2">
            <span className="text-3xl font-bold text-gray-900">
              {summary.daily_workflows_used}
            </span>
            <span className="text-gray-500 text-sm mb-1">
              / {summary.daily_workflow_cap} workflows today
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${
                capPercent >= 100
                  ? "bg-red-500"
                  : capPercent >= 80
                  ? "bg-yellow-500"
                  : "bg-green-500"
              }`}
              style={{ width: `${Math.min(capPercent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {summary.daily_workflow_cap - summary.daily_workflows_used > 0
              ? `${
                  summary.daily_workflow_cap - summary.daily_workflows_used
                } remaining`
              : "Limit reached. Resets at midnight UTC."}
          </p>
        </div>
      </div>

      {/* Daily cost chart (simple bar chart) */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-8">
        <h3 className="text-sm font-medium text-gray-700 mb-4">
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
                  className="bg-blue-400 hover:bg-blue-600 rounded-t transition-colors w-full"
                  style={{ height: `${height}%` }}
                />
                {/* Tooltip on hover */}
                <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1 bg-gray-800 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10">
                  {d.date}: {formatCost(d.total_cost)}
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-xs text-gray-400">
            {daily.length > 0 ? daily[0].date : ""}
          </span>
          <span className="text-xs text-gray-400">
            {daily.length > 0 ? daily[daily.length - 1].date : ""}
          </span>
        </div>
      </div>

      {/* Per-workflow breakdown */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-sm font-medium text-gray-700 mb-4">
          Cost by Workflow
        </h3>
        {summary.workflows.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-8">
            No usage data yet. Create your first content workflow to start
            tracking costs.
          </p>
        ) : (
          <div className="space-y-3">
            {summary.workflows.map((wf) => (
              <Link
                key={wf.workflow_id}
                href={`/content/${wf.workflow_id}`}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition border border-gray-100"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {wf.goal_text}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {wf.step_count} LLM calls &middot;{" "}
                    {formatTokens(
                      wf.total_input_tokens + wf.total_output_tokens
                    )}{" "}
                    tokens
                  </p>
                </div>
                <span className="text-sm font-medium text-gray-700 ml-4">
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
