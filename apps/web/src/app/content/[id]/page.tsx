"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { contentApi, scheduleApi, oauthApi, WorkflowDetail, ContentAsset } from "../../../lib/api";

// ── Supabase Realtime for live status updates ──
import { createClient } from "@/lib/supabase/client";

const STEP_ORDER = [
  "signal_research",
  "gap_analysis",
  "topic_selection",
  "hook_lab",
  "script_generation",
  "editor",
  "testing",
  "approval",
];

const STEP_LABELS: Record<string, string> = {
  signal_research: "Researching signals",
  gap_analysis: "Analyzing gaps",
  topic_selection: "Selecting topics",
  hook_lab: "Generating hooks",
  script_generation: "Writing scripts",
  editor: "Editing content",
  testing: "Running quality tests",
  approval: "Awaiting approval",
};

const PLATFORM_LABELS: Record<string, string> = {
  youtube: "YouTube",
  linkedin: "LinkedIn",
  twitter: "Twitter/X",
  short_form: "Short-form",
};

interface TopicCandidate {
  id: string;
  title: string;
  audience_pain: string;
  opportunity_score: number;
  risk_flags: string[];
  sources: string[];
  score_breakdown: Record<string, number>;
  why_now: string;
}

interface HookCandidate {
  id: string;
  hook_text: string;
  hook_type: string;
  total_score: number;
  score_breakdown: Record<string, number>;
}

export default function WorkflowDetailPage() {
  const params = useParams();
  const workflowId = params.id as string;

  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [assets, setAssets] = useState<ContentAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  // Approval state
  const [rejectFeedback, setRejectFeedback] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const [topics, setTopics] = useState<TopicCandidate[]>([]);
  const [hooks, setHooks] = useState<HookCandidate[]>([]);

  const loadWorkflow = useCallback(async () => {
    try {
      const [wf, a] = await Promise.all([
        contentApi.get(workflowId),
        contentApi.getAssets(workflowId).catch(() => []),
      ]);
      setWorkflow(wf);
      setAssets(a);

      // Fetch topics/hooks based on status
      if (wf.status === "awaiting_topic") {
        const topicData = await contentApi.getTopics(workflowId).catch(() => ({ topics: [] }));
        setTopics(topicData.topics || []);
      }
      if (wf.status === "awaiting_hook") {
        const hookData = await contentApi.getHooks(workflowId).catch(() => ({ hooks: [], selected_topic: null }));
        setHooks(hookData.hooks || []);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  // Initial load
  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);

  // Supabase Realtime subscription for live status updates
  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel(`workflow-${workflowId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "workflows",
          filter: `id=eq.${workflowId}`,
        },
        () => {
          // Reload data when workflow status changes
          loadWorkflow();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [workflowId, loadWorkflow]);

  // ── Topic selection ──
  const handleSelectTopic = async (topicId: string) => {
    setActionLoading(true);
    try {
      await contentApi.selectTopic(workflowId, topicId);
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Hook selection ──
  const handleSelectHook = async (hookId: string) => {
    setActionLoading(true);
    try {
      await contentApi.selectHook(workflowId, hookId);
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Approval ──
  const handleApprove = async () => {
    setActionLoading(true);
    try {
      await contentApi.approve(workflowId, "approved");
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (regenStep?: string) => {
    setActionLoading(true);
    try {
      await contentApi.approve(workflowId, "rejected", rejectFeedback, regenStep);
      setShowRejectForm(false);
      setRejectFeedback("");
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <main className="max-w-4xl mx-auto p-8">
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      </main>
    );
  }

  if (!workflow) {
    return (
      <main className="max-w-4xl mx-auto p-8">
        <div className="text-center py-20">
          <h2 className="text-lg font-medium text-gray-900">Workflow not found</h2>
          <Link href="/content" className="text-sm text-blue-600 hover:underline mt-2 inline-block">
            Back to Content
          </Link>
        </div>
      </main>
    );
  }

  const platforms = workflow.platforms || ["youtube"];

  // Determine step progress
  const currentStepIndex = workflow.current_step
    ? STEP_ORDER.indexOf(workflow.current_step)
    : -1;

  return (
    <main className="max-w-4xl mx-auto p-8">
      <Link
        href="/content"
        className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        &larr; Back to Content
      </Link>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{workflow.goal_text}</h1>
        <div className="flex items-center gap-3 flex-wrap">
          <StatusBadge status={workflow.status} />
          <div className="flex gap-1">
            {platforms.map((p) => (
              <span key={p} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
                {PLATFORM_LABELS[p] || p}
              </span>
            ))}
          </div>
          <span className="text-sm text-gray-400">v{workflow.active_version}</span>
          {workflow.error_message && (
            <span className="text-sm text-red-600">{workflow.error_message}</span>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700 text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* Pipeline Progress */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-700 mb-3">Pipeline Progress</h2>
        <div className="flex items-center gap-1">
          {STEP_ORDER.map((step, i) => {
            const isCompleted = currentStepIndex > i;
            const isCurrent = currentStepIndex === i;
            const isWaiting = workflow.status.startsWith("awaiting") && isCurrent;
            return (
              <div key={step} className="flex-1 flex flex-col items-center">
                <div
                  className={`h-2 w-full rounded-full ${
                    isCompleted
                      ? "bg-green-500"
                      : isCurrent
                      ? isWaiting
                        ? "bg-yellow-400"
                        : "bg-blue-500 animate-pulse"
                      : "bg-gray-200"
                  }`}
                />
                <span className={`text-[10px] mt-1 ${isCurrent ? "text-gray-900 font-medium" : "text-gray-400"}`}>
                  {STEP_LABELS[step]?.split(" ").slice(-1)[0]}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Status-driven content */}
      {(workflow.status === "queued" || workflow.status === "running") && (
        <RunningState step={workflow.current_step} />
      )}

      {workflow.status === "awaiting_topic" && (
        <TopicSelection
          topics={topics}
          onSelect={handleSelectTopic}
          loading={actionLoading}
        />
      )}

      {workflow.status === "awaiting_hook" && (
        <HookSelection
          hooks={hooks}
          onSelect={handleSelectHook}
          loading={actionLoading}
        />
      )}

      {workflow.status === "awaiting_approval" && (
        <ApprovalSection
          workflow={workflow}
          assets={assets}
          onApprove={handleApprove}
          onReject={handleReject}
          showRejectForm={showRejectForm}
          setShowRejectForm={setShowRejectForm}
          rejectFeedback={rejectFeedback}
          setRejectFeedback={setRejectFeedback}
          loading={actionLoading}
        />
      )}

      {(workflow.status === "completed" || workflow.status === "approved") && (
        <CompletedSection workflow={workflow} assets={assets} />
      )}

      {workflow.status === "failed" && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-900 mb-2">Pipeline failed</h3>
          <p className="text-red-700 text-sm">{workflow.error_message || "An unexpected error occurred."}</p>
        </div>
      )}
    </main>
  );
}

// ── Sub-components ──

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    queued: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    awaiting_topic: "bg-yellow-100 text-yellow-700",
    awaiting_hook: "bg-yellow-100 text-yellow-700",
    awaiting_approval: "bg-purple-100 text-purple-700",
    approved: "bg-green-100 text-green-700",
    completed: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
    failed: "bg-red-100 text-red-700",
  };
  const labels: Record<string, string> = {
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
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.queued}`}>
      {labels[status] || status}
    </span>
  );
}

function RunningState({ step }: { step: string | null }) {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-blue-900 mb-1">
        {step ? STEP_LABELS[step] || step : "Starting pipeline..."}
      </h3>
      <p className="text-blue-700 text-sm">
        This page will update automatically when the next step is ready.
      </p>
    </div>
  );
}

function TopicSelection({
  topics,
  onSelect,
  loading,
}: {
  topics: TopicCandidate[];
  onSelect: (id: string) => void;
  loading: boolean;
}) {
  if (topics.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-yellow-900 mb-1">Waiting for topics</h3>
        <p className="text-yellow-700 text-sm">
          The pipeline is generating topic candidates. This page will update when they are ready.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-bold mb-1">Pick a Topic</h2>
      <p className="text-gray-500 text-sm mb-4">
        The AI found {topics.length} topic candidates. Pick the one you want to create content about.
      </p>
      <div className="space-y-3">
        {topics.map((topic) => (
          <div
            key={topic.id}
            className="bg-white border border-gray-200 rounded-lg p-5 hover:border-blue-300 transition"
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-medium text-gray-900 flex-1 pr-4">{topic.title}</h3>
              <span className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-0.5 rounded">
                Score: {topic.opportunity_score}
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-2">{topic.audience_pain}</p>
            {topic.why_now && (
              <p className="text-sm text-gray-500 mb-2">Why now: {topic.why_now}</p>
            )}
            {topic.risk_flags.length > 0 && (
              <div className="flex gap-1 mb-3">
                {topic.risk_flags.map((flag, i) => (
                  <span key={i} className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded">
                    {flag}
                  </span>
                ))}
              </div>
            )}
            <button
              onClick={() => onSelect(topic.id)}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
            >
              {loading ? "Selecting..." : "Select this topic"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function HookSelection({
  hooks,
  onSelect,
  loading,
}: {
  hooks: HookCandidate[];
  onSelect: (id: string) => void;
  loading: boolean;
}) {
  if (hooks.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-yellow-900 mb-1">Waiting for hooks</h3>
        <p className="text-yellow-700 text-sm">
          The pipeline is generating hook candidates. This page will update when they are ready.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-bold mb-1">Pick a Hook</h2>
      <p className="text-gray-500 text-sm mb-4">
        Choose the opening hook for your content. This is what grabs attention in the first few seconds.
      </p>
      <div className="space-y-3">
        {hooks.map((hook) => (
          <div
            key={hook.id}
            className="bg-white border border-gray-200 rounded-lg p-5 hover:border-blue-300 transition"
          >
            <div className="flex items-start justify-between mb-2">
              <p className="text-gray-900 font-medium flex-1 pr-4">"{hook.hook_text}"</p>
              <span className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-0.5 rounded whitespace-nowrap">
                Score: {hook.total_score}
              </span>
            </div>
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                {hook.hook_type}
              </span>
              {Object.entries(hook.score_breakdown || {}).map(([k, v]) => (
                <div key={k} className="flex items-center gap-1">
                  <span className="text-[10px] text-gray-400 uppercase">{k}</span>
                  <div className="w-12 h-1.5 bg-gray-200 rounded-full">
                    <div
                      className="h-1.5 bg-blue-500 rounded-full"
                      style={{ width: `${Math.min(100, (v as number) * 10)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={() => onSelect(hook.id)}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
            >
              {loading ? "Selecting..." : "Use this hook"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function TestReportPanel({ workflow }: { workflow: WorkflowDetail }) {
  const testReport = (workflow.settings as any)?._test_report || [];

  if (testReport.length === 0) return null;

  const passed = testReport.filter((t: any) => t.passed).length;
  const failed = testReport.length - passed;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-700">Quality Test Report</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">{passed} passed</span>
          {failed > 0 && (
            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">{failed} failed</span>
          )}
        </div>
      </div>
      <div className="space-y-2">
        {testReport.map((test: any, i: number) => (
          <div key={i} className={`flex items-start gap-2 text-sm rounded p-2 ${test.passed ? "bg-green-50" : "bg-red-50"}`}>
            <span className={`mt-0.5 ${test.passed ? "text-green-600" : "text-red-600"}`}>
              {test.passed ? "✓" : "✗"}
            </span>
            <div className="flex-1">
              <span className="font-medium text-gray-900">{test.asset_type}</span>
              {test.issues && test.issues.length > 0 && (
                <ul className="mt-1 space-y-0.5">
                  {test.issues.map((issue: string, j: number) => (
                    <li key={j} className="text-xs text-red-600">{issue}</li>
                  ))}
                </ul>
              )}
              {test.risk_flags && test.risk_flags.length > 0 && (
                <div className="flex gap-1 mt-1">
                  {test.risk_flags.map((flag: string, j: number) => (
                    <span key={j} className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">{flag}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApprovalSection({
  workflow,
  assets,
  onApprove,
  onReject,
  showRejectForm,
  setShowRejectForm,
  rejectFeedback,
  setRejectFeedback,
  loading,
}: {
  workflow: WorkflowDetail;
  assets: ContentAsset[];
  onApprove: () => void;
  onReject: (step?: string) => void;
  showRejectForm: boolean;
  setShowRejectForm: (v: boolean) => void;
  rejectFeedback: string;
  setRejectFeedback: (v: string) => void;
  loading: boolean;
}) {
  const [activeTab, setActiveTab] = useState(
    (workflow.platforms || ["youtube"])[0]
  );
  const platforms = workflow.platforms || ["youtube"];
  const contentPack = (workflow.settings as any)?._content_pack ||
    (workflow.settings as any)?._edited_pack || {};

  return (
    <div>
      <h2 className="text-lg font-bold mb-4">Review Your Content</h2>

      {/* Test Report */}
      <TestReportPanel workflow={workflow} />

      {/* Platform tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-4">
        {platforms.map((p) => (
          <button
            key={p}
            onClick={() => setActiveTab(p)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === p
                ? "border-blue-500 text-blue-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {PLATFORM_LABELS[p] || p}
          </button>
        ))}
      </div>

      {/* Content preview */}
      <ContentPreview platform={activeTab} contentPack={contentPack} assets={assets} editable />

      {/* Action buttons */}
      <div className="flex items-center gap-3 mt-6 pt-6 border-t border-gray-200">
        <button
          onClick={onApprove}
          disabled={loading}
          className="px-5 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
        >
          {loading ? "Processing..." : "Approve All"}
        </button>
        <button
          onClick={() => setShowRejectForm(!showRejectForm)}
          className="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
        >
          Reject with Feedback
        </button>
      </div>

      {showRejectForm && (
        <div className="mt-4 bg-gray-50 rounded-lg p-4">
          <textarea
            value={rejectFeedback}
            onChange={(e) => setRejectFeedback(e.target.value)}
            placeholder="What should be different? Be specific about what to change..."
            className="w-full border border-gray-300 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={3}
          />
          <div className="flex items-center gap-3 mt-3">
            <button
              onClick={() => onReject("script_generation")}
              disabled={loading || !rejectFeedback.trim()}
              className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition disabled:opacity-50"
            >
              Regenerate from Script
            </button>
            <button
              onClick={() => onReject("hook_lab")}
              disabled={loading || !rejectFeedback.trim()}
              className="px-4 py-2 border border-red-300 text-red-700 rounded-lg text-sm font-medium hover:bg-red-50 transition disabled:opacity-50"
            >
              Regenerate from Hook
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ContentPreview({
  platform,
  contentPack,
  assets,
  editable,
  onSaveEdit,
}: {
  platform: string;
  contentPack: Record<string, any>;
  assets: ContentAsset[];
  editable?: boolean;
  onSaveEdit?: (assetId: string, body: Record<string, any>) => void;
}) {
  // Try to show content from assets first, fall back to contentPack
  const platformAssets = assets.filter((a) => a.platform === platform || (!a.platform && platform === "youtube"));

  if (platformAssets.length === 0 && Object.keys(contentPack).length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p>No content available for this platform yet.</p>
      </div>
    );
  }

  // Platform-specific content rendering from contentPack
  if (platform === "youtube") {
    return <YouTubePreview contentPack={contentPack} />;
  }
  if (platform === "linkedin") {
    return <LinkedInPreview posts={contentPack.linkedin_posts || []} />;
  }
  if (platform === "twitter") {
    return (
      <TwitterPreview
        posts={contentPack.twitter_posts || []}
        thread={contentPack.twitter_thread || null}
      />
    );
  }
  if (platform === "short_form") {
    return <ShortFormPreview scripts={contentPack.short_form_scripts || []} />;
  }

  // Fallback
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <pre className="text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
        {JSON.stringify(contentPack, null, 2)}
      </pre>
    </div>
  );
}

function YouTubePreview({ contentPack }: { contentPack: Record<string, any> }) {
  const longScript = contentPack.youtube_long || {};
  const shorts = contentPack.youtube_shorts || [];
  const titles = contentPack.titles || [];
  const description = contentPack.description || "";
  const tags = contentPack.tags || [];
  const thumbnails = contentPack.thumbnail_brief || [];

  return (
    <div className="space-y-6">
      {/* Long Script */}
      {longScript.sections && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded font-medium">Long Script</span>
            <span className="text-sm text-gray-500">
              ~{longScript.estimated_duration_minutes || "?"}min, {longScript.word_count || "?"} words
            </span>
          </div>
          {longScript.hook && (
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 mb-4">
              <p className="text-sm font-medium text-yellow-800">Hook</p>
              <p className="text-sm text-yellow-900 mt-1">{longScript.hook}</p>
            </div>
          )}
          <div className="space-y-4">
            {(longScript.sections || []).map((section: any, i: number) => (
              <div key={i} className="border-l-2 border-gray-200 pl-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-400 font-mono">{section.timestamp || ""}</span>
                  <span className="text-sm font-medium text-gray-900">{section.heading}</span>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{section.script}</p>
                {section.broll_suggestion && (
                  <p className="text-xs text-gray-400 mt-1 italic">B-roll: {section.broll_suggestion}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Shorts */}
      {shorts.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">YouTube Shorts ({shorts.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {shorts.map((short: any, i: number) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-xs text-gray-400 mb-1">~{short.estimated_duration_seconds || "?"}s</p>
                <p className="text-sm font-medium text-gray-900 mb-2">"{short.hook}"</p>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{short.script}</p>
                {short.cta && <p className="text-xs text-blue-600 mt-2">CTA: {short.cta}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Titles */}
      {titles.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Title Options ({titles.length})</h3>
          <ol className="space-y-1">
            {titles.map((title: string, i: number) => (
              <li key={i} className="text-sm text-gray-700 flex gap-2">
                <span className="text-gray-400 shrink-0">{i + 1}.</span>
                {title}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Description + Tags */}
      {description && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{description}</p>
        </div>
      )}
      {tags.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {tags.map((tag: string, i: number) => (
            <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{tag}</span>
          ))}
        </div>
      )}

      {/* Thumbnail Briefs */}
      {thumbnails.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Thumbnail Concepts ({thumbnails.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {thumbnails.map((tb: any, i: number) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm font-medium text-gray-900">{tb.text_overlay}</p>
                <p className="text-xs text-gray-600 mt-1">{tb.concept}</p>
                {tb.emotion && <p className="text-xs text-gray-400">Emotion: {tb.emotion}</p>}
                {tb.color_scheme && <p className="text-xs text-gray-400">Colors: {tb.color_scheme}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LinkedInPreview({ posts }: { posts: any[] }) {
  if (posts.length === 0) return <p className="text-gray-400 text-center py-8">No LinkedIn posts generated.</p>;

  const typeLabels: Record<string, string> = {
    story: "Story Post",
    tactical: "Tactical List",
    contrarian: "Contrarian Take",
  };

  return (
    <div className="space-y-4">
      {posts.map((post: any, i: number) => (
        <div key={i} className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-medium">
              {typeLabels[post.post_type] || post.post_type}
            </span>
            <span className="text-xs text-gray-400">{post.char_count || "?"} chars</span>
          </div>
          {post.hook_line && (
            <p className="text-sm font-medium text-gray-900 mb-2">{post.hook_line}</p>
          )}
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{post.body}</p>
          {post.cta && (
            <p className="text-sm text-blue-600 mt-3 pt-3 border-t border-gray-100">{post.cta}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function TwitterPreview({ posts, thread }: { posts: any[]; thread: any }) {
  return (
    <div className="space-y-6">
      {/* Standalone tweets */}
      {posts.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Standalone Tweets ({posts.length})</h3>
          <div className="space-y-3">
            {posts.map((tweet: any, i: number) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-900">{tweet.tweet_text}</p>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs text-gray-400">{tweet.char_count || "?"}/280 chars</span>
                  <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{tweet.angle}</span>
                  {(tweet.char_count || 0) > 280 && (
                    <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded">OVER LIMIT</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Thread */}
      {thread && thread.hook_tweet && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Thread ({thread.total_tweets || (thread.tweets || []).length + 1} tweets)
          </h3>
          <div className="border-l-2 border-blue-200 pl-4 space-y-3">
            <div className="bg-white border border-blue-200 rounded-lg p-4">
              <p className="text-xs text-blue-500 font-medium mb-1">1/</p>
              <p className="text-sm text-gray-900">{thread.hook_tweet}</p>
            </div>
            {(thread.tweets || []).map((tweet: string, i: number) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-xs text-gray-400 font-medium mb-1">{i + 2}/</p>
                <p className="text-sm text-gray-900">{tweet}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ShortFormPreview({ scripts }: { scripts: any[] }) {
  if (scripts.length === 0) return <p className="text-gray-400 text-center py-8">No short-form scripts generated.</p>;

  const angleLabels: Record<string, string> = {
    hot_take: "Hot Take",
    tactical: "Quick Tip",
    story: "Story",
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {scripts.map((script: any, i: number) => (
        <div key={i} className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded font-medium">
              {angleLabels[script.angle] || script.angle}
            </span>
            <span className="text-xs text-gray-400">~{script.estimated_seconds || "?"}s</span>
          </div>
          <div className="bg-yellow-50 rounded p-2 mb-3">
            <p className="text-xs text-yellow-700 font-medium">Hook (first 2s)</p>
            <p className="text-sm text-yellow-900">{script.hook}</p>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap mb-3">{script.script}</p>
          {script.on_screen_text && (
            <div className="bg-gray-50 rounded p-2 mb-2">
              <p className="text-xs text-gray-500 font-medium">On-screen text</p>
              {Array.isArray(script.on_screen_text)
                ? script.on_screen_text.map((t: string, j: number) => (
                    <p key={j} className="text-xs text-gray-700">{t}</p>
                  ))
                : <p className="text-xs text-gray-700">{script.on_screen_text}</p>
              }
            </div>
          )}
          {script.punchline && <p className="text-xs text-gray-600">Punchline: {script.punchline}</p>}
          {script.cta && <p className="text-xs text-blue-600 mt-1">CTA: {script.cta}</p>}
          {script.visual_direction && (
            <p className="text-xs text-gray-400 mt-2 italic">Visual: {script.visual_direction}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function ExportBar({ workflowId }: { workflowId: string }) {
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const [googleLoading, setGoogleLoading] = useState(false);
  const [notionLoading, setNotionLoading] = useState(false);
  const [exportMsg, setExportMsg] = useState("");
  const [googleConnected, setGoogleConnected] = useState<boolean | null>(null);
  const [notionConnected, setNotionConnected] = useState<boolean | null>(null);

  // Check OAuth connection status on mount
  useEffect(() => {
    oauthApi.googleStatus().then(s => setGoogleConnected(s.connected)).catch(() => setGoogleConnected(false));
    oauthApi.notionStatus().then(s => setNotionConnected(s.connected)).catch(() => setNotionConnected(false));
  }, []);

  const handleCopyClipboard = async () => {
    try {
      const result = await contentApi.exportClipboard(workflowId);
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      alert("Failed to copy to clipboard");
    }
  };

  const handleDownloadMarkdown = async () => {
    setDownloading(true);
    try {
      const md = await contentApi.exportMarkdown(workflowId);
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `content-${workflowId.slice(0, 8)}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Failed to download markdown");
    } finally {
      setDownloading(false);
    }
  };

  const handleGoogleDocsExport = async () => {
    if (!googleConnected) {
      // Redirect to Google OAuth
      try {
        const { url } = await oauthApi.googleAuthUrl();
        window.location.href = url;
      } catch (e: any) {
        setExportMsg(e.message || "Google not configured");
        setTimeout(() => setExportMsg(""), 4000);
      }
      return;
    }
    setGoogleLoading(true);
    setExportMsg("");
    try {
      const result = await contentApi.exportGoogleDocs(workflowId);
      window.open(result.url, "_blank");
      setExportMsg("Google Doc created");
      setTimeout(() => setExportMsg(""), 3000);
    } catch (e: any) {
      setExportMsg(e.message || "Google Docs export failed");
      setTimeout(() => setExportMsg(""), 4000);
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleNotionExport = async () => {
    if (!notionConnected) {
      // Redirect to Notion OAuth
      try {
        const { url } = await oauthApi.notionAuthUrl();
        window.location.href = url;
      } catch (e: any) {
        setExportMsg(e.message || "Notion not configured");
        setTimeout(() => setExportMsg(""), 4000);
      }
      return;
    }
    setNotionLoading(true);
    setExportMsg("");
    try {
      const result = await contentApi.exportNotion(workflowId);
      window.open(result.url, "_blank");
      setExportMsg("Notion page created");
      setTimeout(() => setExportMsg(""), 3000);
    } catch (e: any) {
      setExportMsg(e.message || "Notion export failed");
      setTimeout(() => setExportMsg(""), 4000);
    } finally {
      setNotionLoading(false);
    }
  };

  const handleImportToSchedule = async () => {
    setImporting(true);
    setImportMsg("");
    try {
      const result = await scheduleApi.importFromWorkflow(workflowId);
      setImportMsg(`Imported ${result.imported} items to schedule`);
      setTimeout(() => setImportMsg(""), 3000);
    } catch (e: any) {
      setImportMsg(e.message || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-green-900 font-medium">Content approved and ready</h3>
          <p className="text-green-700 text-sm mt-1">
            Your content has been generated, edited, tested, and approved.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={handleCopyClipboard}
            className="px-4 py-2 bg-white border border-green-300 text-green-700 rounded-lg text-sm font-medium hover:bg-green-50 transition"
          >
            {copied ? "Copied!" : "Copy to clipboard"}
          </button>
          <button
            onClick={handleDownloadMarkdown}
            disabled={downloading}
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
          >
            {downloading ? "Downloading..." : "Download .md"}
          </button>
          <button
            onClick={handleGoogleDocsExport}
            disabled={googleLoading}
            className="px-4 py-2 bg-white border border-blue-400 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-50 transition disabled:opacity-50"
            title={googleConnected ? "Send to Google Docs" : "Connect Google account first"}
          >
            {googleLoading ? "Creating..." : googleConnected ? "Google Docs" : "Connect Google"}
          </button>
          <button
            onClick={handleNotionExport}
            disabled={notionLoading}
            className="px-4 py-2 bg-white border border-gray-800 text-gray-800 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50"
            title={notionConnected ? "Send to Notion" : "Connect Notion account first"}
          >
            {notionLoading ? "Creating..." : notionConnected ? "Notion" : "Connect Notion"}
          </button>
          <button
            onClick={handleImportToSchedule}
            disabled={importing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
          >
            {importing ? "Importing..." : "Add to Schedule"}
          </button>
        </div>
      </div>
      {importMsg && (
        <p className="text-sm text-green-800 mt-2">{importMsg}</p>
      )}
      {exportMsg && (
        <p className="text-sm text-blue-800 mt-2">{exportMsg}</p>
      )}
    </div>
  );
}

function VersionHistoryPanel({ workflowId, assets }: { workflowId: string; assets: ContentAsset[] }) {
  const [open, setOpen] = useState(false);
  const [versions, setVersions] = useState<Record<string, ContentAsset[]>>({});
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);

  // Only show if there are versioned assets (version > 1)
  const hasVersions = assets.some((a) => a.version > 1);
  if (!hasVersions && !open) return null;

  const loadVersions = async (assetId: string) => {
    if (versions[assetId]) return;
    setLoadingId(assetId);
    try {
      const vList = await contentApi.getAssetVersions(workflowId, assetId);
      setVersions((prev) => ({ ...prev, [assetId]: vList }));
    } catch {
      // silently fail
    } finally {
      setLoadingId(null);
    }
  };

  const handleRestore = async (assetId: string) => {
    setRestoring(true);
    try {
      await contentApi.restoreAssetVersion(workflowId, assetId);
      window.location.reload();
    } catch {
      alert("Failed to restore version");
    } finally {
      setRestoring(false);
    }
  };

  // Group latest assets by type for display
  const latestAssets = assets.filter((a) => a.is_latest !== false);

  return (
    <div className="mt-6 border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition text-sm font-medium text-gray-700"
      >
        <span>Version History ({latestAssets.length} assets)</span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="p-4 space-y-3">
          {latestAssets.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">No assets found.</p>
          ) : (
            latestAssets.map((asset) => (
              <div key={asset.id} className="border border-gray-100 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-medium">
                      {asset.asset_type}
                    </span>
                    <span className="text-xs text-gray-400">v{asset.version}</span>
                    {asset.version > 1 && (
                      <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
                        edited
                      </span>
                    )}
                  </div>
                  {asset.version > 1 && (
                    <button
                      onClick={() => loadVersions(asset.id)}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      {loadingId === asset.id ? "Loading..." : versions[asset.id] ? "Hide versions" : "Show older versions"}
                    </button>
                  )}
                </div>
                {asset.feedback && (
                  <p className="text-xs text-gray-500 italic mb-2">{asset.feedback}</p>
                )}

                {/* Version list */}
                {versions[asset.id] && (
                  <div className="mt-2 pl-3 border-l-2 border-gray-200 space-y-2">
                    {versions[asset.id].map((v) => (
                      <div
                        key={v.id}
                        className={`flex items-center justify-between p-2 rounded text-xs ${
                          v.is_latest ? "bg-blue-50" : "bg-gray-50"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium">v{v.version}</span>
                          <span className="text-gray-400">
                            {new Date(v.created_at).toLocaleString()}
                          </span>
                          {v.is_latest && (
                            <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">current</span>
                          )}
                          {v.feedback && (
                            <span className="text-gray-500 italic">{v.feedback}</span>
                          )}
                        </div>
                        {!v.is_latest && (
                          <button
                            onClick={() => handleRestore(v.id)}
                            disabled={restoring}
                            className="text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50"
                          >
                            Restore
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function CompletedSection({
  workflow,
  assets,
}: {
  workflow: WorkflowDetail;
  assets: ContentAsset[];
}) {
  const [activeTab, setActiveTab] = useState(
    (workflow.platforms || ["youtube"])[0]
  );
  const platforms = workflow.platforms || ["youtube"];
  const contentPack = (workflow.settings as any)?._content_pack ||
    (workflow.settings as any)?._edited_pack || {};

  return (
    <div>
      <ExportBar workflowId={workflow.id} />

      {/* Test Report */}
      <TestReportPanel workflow={workflow} />

      {/* Platform tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-4">
        {platforms.map((p) => (
          <button
            key={p}
            onClick={() => setActiveTab(p)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === p
                ? "border-blue-500 text-blue-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {PLATFORM_LABELS[p] || p}
          </button>
        ))}
      </div>

      <ContentPreview platform={activeTab} contentPack={contentPack} assets={assets} />

      {/* Version history */}
      <VersionHistoryPanel workflowId={workflow.id} assets={assets} />
    </div>
  );
}
