"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { contentApi, WorkflowDetail, ContentAsset, StepSnapshot } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

import { TopicCandidate, HookCandidate } from "./types";
import { ComposerLayout } from "./components/composer-layout";
import { ComposerSkeleton } from "./components/composer-skeleton";
import { PanelErrorBoundary } from "./components/panel-error-boundary";
import { LeftSidebar } from "./components/left-sidebar";
import { CenterEditor } from "./components/center-editor";
import { RightPreview } from "./components/right-preview";

export default function WorkflowDetailPage() {
  const params = useParams();
  const workflowId = params.id as string;

  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [assets, setAssets] = useState<ContentAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [executing, setExecuting] = useState(false);

  const [topics, setTopics] = useState<TopicCandidate[]>([]);
  const [hooks, setHooks] = useState<HookCandidate[]>([]);
  const [snapshots, setSnapshots] = useState<StepSnapshot[]>([]);

  // Guard to prevent duplicate execute calls
  const executingRef = useRef(false);

  // ── Data loading ──

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
        const topicData = await contentApi
          .getTopics(workflowId)
          .catch(() => ({ topics: [] }));
        setTopics(topicData.topics || []);
      }
      if (wf.status === "awaiting_hook") {
        const hookData = await contentApi
          .getHooks(workflowId)
          .catch(() => ({ hooks: [], selected_topic: null }));
        setHooks(hookData.hooks || []);
      }

      // Load snapshots for step detail expansion (non-blocking)
      contentApi
        .getSnapshots(workflowId)
        .then((data) => setSnapshots(data.snapshots || []))
        .catch(() => {});
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

  // ── Auto-execute: when workflow is "queued", run pipeline inline ──

  useEffect(() => {
    if (!workflow) return;
    if (workflow.status !== "queued") return;
    if (executingRef.current) return;

    executingRef.current = true;
    setExecuting(true);

    contentApi
      .execute(workflowId)
      .then(() => loadWorkflow())
      .catch((err) => {
        console.error("[execute] Pipeline execution failed:", err.message);
        loadWorkflow(); // Reload to show actual status (might be "failed")
      })
      .finally(() => {
        executingRef.current = false;
        setExecuting(false);
      });
  }, [workflow?.status, workflowId, loadWorkflow]);

  // ── Supabase Realtime for live status updates ──

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
          loadWorkflow();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [workflowId, loadWorkflow]);

  // ── User actions (with inline execute) ──

  const handleSelectTopic = async (topicId: string) => {
    setActionLoading(true);
    try {
      await contentApi.selectTopic(workflowId, topicId);
      // Topic selection re-queues the workflow. Execute inline.
      setExecuting(true);
      await contentApi.execute(workflowId);
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
      await loadWorkflow();
    } finally {
      setActionLoading(false);
      setExecuting(false);
    }
  };

  const handleSelectHook = async (hookId: string) => {
    setActionLoading(true);
    try {
      await contentApi.selectHook(workflowId, hookId);
      // Hook selection re-queues the workflow. Execute inline.
      setExecuting(true);
      await contentApi.execute(workflowId);
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
      await loadWorkflow();
    } finally {
      setActionLoading(false);
      setExecuting(false);
    }
  };

  const handleApprove = async () => {
    setActionLoading(true);
    try {
      await contentApi.approve(workflowId, "approved");
      // Approval re-queues the workflow. Execute inline.
      setExecuting(true);
      await contentApi.execute(workflowId);
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
      await loadWorkflow();
    } finally {
      setActionLoading(false);
      setExecuting(false);
    }
  };

  const handleReject = async (feedback: string, regenStep?: string) => {
    setActionLoading(true);
    try {
      await contentApi.approve(workflowId, "rejected", feedback, regenStep);
      // Rejection re-queues the workflow. Execute inline.
      setExecuting(true);
      await contentApi.execute(workflowId);
      await loadWorkflow();
    } catch (e: any) {
      setError(e.message);
      await loadWorkflow();
    } finally {
      setActionLoading(false);
      setExecuting(false);
    }
  };

  // ── Loading / error states ──

  if (loading) {
    return <ComposerSkeleton />;
  }

  // Show a visual progress indicator while the pipeline executes inline
  if (executing || (workflow && workflow.status === "queued")) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-64px)] bg-background">
        <div className="text-center max-w-md">
          <div className="mb-4">
            <svg className="animate-spin h-10 w-10 text-primary mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-foreground mb-2">
            Running Pipeline...
          </h2>
          <p className="text-muted-foreground text-sm mb-2">
            The AI is researching trends, analyzing gaps, and generating topic candidates.
          </p>
          <p className="text-muted-foreground text-xs">
            This usually takes 30 to 90 seconds. The page will update automatically.
          </p>
        </div>
      </div>
    );
  }

  if (error && !workflow) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-64px)] bg-background">
        <div className="text-center max-w-sm">
          <div className="text-4xl mb-3">&#x26A0;&#xFE0F;</div>
          <h2 className="text-lg font-bold text-foreground mb-2">
            Failed to load workflow
          </h2>
          <p className="text-muted-foreground text-sm mb-4">{error}</p>
          <Link
            href="/content"
            className="text-primary hover:text-primary text-sm font-medium"
          >
            Back to Content
          </Link>
        </div>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-64px)] bg-background">
        <div className="text-center">
          <div className="text-4xl mb-3">&#x1F50D;</div>
          <h2 className="text-lg font-bold text-foreground mb-2">
            Workflow not found
          </h2>
          <Link
            href="/content"
            className="text-primary hover:text-primary text-sm font-medium"
          >
            Back to Content
          </Link>
        </div>
      </div>
    );
  }

  // ── 3-panel Composer Layout ──

  return (
    <ComposerLayout
      sidebar={
        <PanelErrorBoundary panelName="Sidebar">
          <LeftSidebar
            workflow={workflow}
            assets={assets}
            snapshots={snapshots}
            onRefresh={loadWorkflow}
          />
        </PanelErrorBoundary>
      }
      editor={
        <PanelErrorBoundary panelName="Editor">
          <CenterEditor
            workflow={workflow}
            assets={assets}
            topics={topics}
            hooks={hooks}
            actionLoading={actionLoading}
            onSelectTopic={handleSelectTopic}
            onSelectHook={handleSelectHook}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        </PanelErrorBoundary>
      }
      preview={
        <PanelErrorBoundary panelName="Preview">
          <RightPreview workflow={workflow} assets={assets} />
        </PanelErrorBoundary>
      }
    />
  );
}
