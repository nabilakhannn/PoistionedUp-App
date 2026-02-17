"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { contentApi, WorkflowSummary, brandApi, BrandCompleteness } from "../../lib/api";

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  queued: { bg: "bg-gray-100", text: "text-gray-700", label: "Queued" },
  running: { bg: "bg-blue-100", text: "text-blue-700", label: "Running" },
  awaiting_topic: { bg: "bg-yellow-100", text: "text-yellow-700", label: "Pick a Topic" },
  awaiting_hook: { bg: "bg-yellow-100", text: "text-yellow-700", label: "Pick a Hook" },
  awaiting_approval: { bg: "bg-purple-100", text: "text-purple-700", label: "Review Content" },
  approved: { bg: "bg-green-100", text: "text-green-700", label: "Done" },
  completed: { bg: "bg-green-100", text: "text-green-700", label: "Done" },
  rejected: { bg: "bg-red-100", text: "text-red-700", label: "Rejected" },
  failed: { bg: "bg-red-100", text: "text-red-700", label: "Failed" },
};

const PLATFORM_LABELS: Record<string, string> = {
  youtube: "YouTube",
  linkedin: "LinkedIn",
  twitter: "Twitter/X",
  short_form: "Short-form",
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.queued;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

function PlatformTags({ platforms }: { platforms: string[] }) {
  return (
    <div className="flex gap-1 flex-wrap">
      {platforms.map((p) => (
        <span key={p} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
          {PLATFORM_LABELS[p] || p}
        </span>
      ))}
    </div>
  );
}

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function ContentDashboard() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [brandReady, setBrandReady] = useState<boolean | null>(null);

  useEffect(() => {
    Promise.all([
      contentApi.list(),
      brandApi.getCompleteness(),
    ])
      .then(([wfs, comp]) => {
        setWorkflows(wfs);
        setBrandReady(comp.overall_percent >= 50);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Content</h1>
          <p className="text-gray-600 mt-1">
            Create scripts, posts, and short-form content from your brand.
          </p>
        </div>
        {brandReady === false ? (
          <Link
            href="/brand"
            className="px-4 py-2.5 bg-gray-200 text-gray-500 rounded-lg text-sm font-medium cursor-not-allowed"
            title="Complete your brand profile first (at least 50%)"
          >
            Complete Brand First
          </Link>
        ) : (
          <Link
            href="/content/new"
            className="px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
          >
            + New Content
          </Link>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      {brandReady === false && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-yellow-800 text-sm font-medium">Brand profile incomplete</p>
          <p className="text-yellow-700 text-sm mt-1">
            You need to complete at least 50% of your brand profile before creating content.
            The AI needs your brand foundation, audience, and offer info to write good scripts.
          </p>
          <Link
            href="/brand"
            className="inline-block mt-3 text-sm text-yellow-800 underline hover:text-yellow-900"
          >
            Go to Brand Builder
          </Link>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : workflows.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-gray-200 rounded-xl">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-1">No content yet</h3>
          <p className="text-gray-500 text-sm mb-4">
            Create your first content workflow to generate scripts, posts, and more.
          </p>
          {brandReady !== false && (
            <Link
              href="/content/new"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
            >
              + New Content
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {workflows.map((wf) => (
            <Link
              key={wf.id}
              href={`/content/${wf.id}`}
              className="block bg-white border border-gray-200 rounded-lg p-5 hover:border-blue-300 hover:shadow-sm transition"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-medium text-gray-900 line-clamp-2 flex-1 pr-4">
                  {wf.goal_text}
                </h3>
                <StatusBadge status={wf.status} />
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <PlatformTags platforms={wf.platforms} />
                <span>v{wf.active_version}</span>
                {wf.current_step && (
                  <span className="text-gray-400">Step: {wf.current_step}</span>
                )}
                {wf.estimated_cost > 0 && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-50 text-green-700 border border-green-200">
                    ${wf.estimated_cost < 0.01 ? wf.estimated_cost.toFixed(4) : wf.estimated_cost.toFixed(2)}
                  </span>
                )}
                <span className="ml-auto">{timeAgo(wf.updated_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
