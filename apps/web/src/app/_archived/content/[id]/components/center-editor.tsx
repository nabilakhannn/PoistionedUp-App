"use client";

import { ContentAsset, WorkflowDetail } from "@/lib/api";
import { TopicCandidate, HookCandidate } from "../types";
import { StatusBadge } from "./status-badge";
import { RunningState } from "./running-state";
import { TopicSelection } from "./topic-selection";
import { HookSelection } from "./hook-selection";
import { ApprovalSection } from "./approval-section";
import { CompletedSection } from "./completed-section";

interface CenterEditorProps {
  workflow: WorkflowDetail;
  assets: ContentAsset[];
  topics: TopicCandidate[];
  hooks: HookCandidate[];
  actionLoading: boolean;
  onSelectTopic: (id: string) => void;
  onSelectHook: (id: string) => void;
  onApprove: () => void;
  onReject: (feedback: string, regenStep?: string) => void;
}

export function CenterEditor({
  workflow,
  assets,
  topics,
  hooks,
  actionLoading,
  onSelectTopic,
  onSelectHook,
  onApprove,
  onReject,
}: CenterEditorProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">
            {workflow.goal_text || "Untitled Workflow"}
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            {workflow.content_type || "content"} &middot; created{" "}
            {new Date(workflow.created_at).toLocaleDateString()}
          </p>
        </div>
        <StatusBadge status={workflow.status} />
      </div>

      {/* Status-driven content */}
      {renderStatusContent({
        workflow,
        assets,
        topics,
        hooks,
        actionLoading,
        onSelectTopic,
        onSelectHook,
        onApprove,
        onReject,
      })}
    </div>
  );
}

function renderStatusContent(props: CenterEditorProps) {
  const {
    workflow,
    assets,
    topics,
    hooks,
    actionLoading,
    onSelectTopic,
    onSelectHook,
    onApprove,
    onReject,
  } = props;
  const status = workflow.status;

  switch (status) {
    case "queued":
      return (
        <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-8 text-center">
          <div className="text-4xl mb-3">&#x23F3;</div>
          <h3 className="text-lg font-medium text-white mb-1">In the Queue</h3>
          <p className="text-zinc-400 text-sm">
            Your workflow is waiting to start. The pipeline will begin shortly.
          </p>
        </div>
      );

    case "running":
      return <RunningState step={workflow.current_step} />;

    case "awaiting_topic":
      return (
        <TopicSelection
          topics={topics}
          onSelect={onSelectTopic}
          loading={actionLoading}
        />
      );

    case "awaiting_hook":
      return (
        <HookSelection
          hooks={hooks}
          onSelect={onSelectHook}
          loading={actionLoading}
        />
      );

    case "awaiting_approval":
      return (
        <ApprovalSection
          workflow={workflow}
          assets={assets}
          onApprove={onApprove}
          onReject={onReject}
          loading={actionLoading}
        />
      );

    case "completed":
    case "approved":
      return <CompletedSection workflow={workflow} assets={assets} />;

    case "rejected":
      return (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-8 text-center">
          <div className="text-4xl mb-3">&#x1F504;</div>
          <h3 className="text-lg font-medium text-red-400 mb-1">
            Sent Back for Changes
          </h3>
          <p className="text-zinc-400 text-sm">
            You rejected this draft with feedback. The pipeline will
            regenerate with your notes.
          </p>
          {(workflow.settings as any)?.rejection_feedback && (
            <div className="mt-4 bg-zinc-900 rounded-lg p-3 text-sm text-zinc-300 text-left max-w-md mx-auto">
              <span className="text-xs text-zinc-500 block mb-1">
                Your feedback:
              </span>
              {(workflow.settings as any).rejection_feedback}
            </div>
          )}
        </div>
      );

    case "failed":
      return (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-8 text-center">
          <div className="text-4xl mb-3">&#x26A0;&#xFE0F;</div>
          <h3 className="text-lg font-medium text-red-400 mb-1">
            Pipeline Failed
          </h3>
          <p className="text-zinc-400 text-sm">
            Something went wrong during{" "}
            {workflow.current_step
              ? `the "${workflow.current_step}" step`
              : "execution"}
            . Check the logs or try running a new workflow.
          </p>
        </div>
      );

    default:
      return (
        <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-6 text-center">
          <p className="text-zinc-400 text-sm">
            Unknown status: <code className="text-white">{status}</code>
          </p>
        </div>
      );
  }
}
