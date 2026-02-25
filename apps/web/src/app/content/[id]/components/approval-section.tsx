"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { ContentAsset, WorkflowDetail } from "@/lib/api";
import { PLATFORM_LABELS } from "../types";
import { ContentPreview } from "./content-preview";
import { TestReportPanel } from "./test-report";

interface ApprovalSectionProps {
  workflow: WorkflowDetail;
  assets: ContentAsset[];
  onApprove: () => void;
  onReject: (feedback: string, regenStep?: string) => void;
  loading: boolean;
}

export function ApprovalSection({
  workflow,
  assets,
  onApprove,
  onReject,
  loading,
}: ApprovalSectionProps) {
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectFeedback, setRejectFeedback] = useState("");
  const rejectTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Keyboard shortcuts: Esc closes the reject form
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && showRejectForm) {
        setShowRejectForm(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showRejectForm]);

  // Auto-focus reject textarea when it opens
  useEffect(() => {
    if (showRejectForm && rejectTextareaRef.current) {
      rejectTextareaRef.current.focus();
    }
  }, [showRejectForm]);
  const platforms = workflow.platforms || ["youtube"];
  const [activeTab, setActiveTab] = useState(platforms[0]);

  // Local editable content pack
  const rawPack =
    (workflow.settings as any)?._content_pack ||
    (workflow.settings as any)?._edited_pack ||
    {};
  const [contentPack, setContentPack] = useState<Record<string, any>>(rawPack);

  const handleContentChange = useCallback(
    (key: string, value: any) => {
      setContentPack((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-white">Review Your Content</h2>

      {/* Test Report */}
      <TestReportPanel workflow={workflow} />

      {/* Platform tabs */}
      <div className="flex gap-1 border-b border-zinc-700/50 mb-4">
        {platforms.map((p) => (
          <button
            key={p}
            onClick={() => setActiveTab(p)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === p
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {PLATFORM_LABELS[p] || p}
          </button>
        ))}
      </div>

      {/* Content preview with inline editing */}
      <ContentPreview
        platform={activeTab}
        contentPack={contentPack}
        assets={assets}
        editable
        onContentChange={handleContentChange}
      />

      {/* Action buttons */}
      <div className="flex items-center gap-3 mt-6 pt-4 border-t border-zinc-700/50">
        <button
          onClick={onApprove}
          disabled={loading}
          className="px-5 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 transition disabled:opacity-50"
        >
          {loading ? "Processing..." : "Approve All"}
        </button>
        <button
          onClick={() => setShowRejectForm(!showRejectForm)}
          className="px-5 py-2.5 border border-zinc-600 text-zinc-300 rounded-lg text-sm font-medium hover:bg-zinc-800 transition"
        >
          Reject with Feedback
        </button>
      </div>

      {showRejectForm && (
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
          <textarea
            ref={rejectTextareaRef}
            value={rejectFeedback}
            onChange={(e) => setRejectFeedback(e.target.value)}
            placeholder="What should be different? Be specific about what to change... (Esc to cancel)"
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm text-white placeholder-zinc-500 resize-none focus:outline-none focus:ring-2 focus:ring-red-500/50"
            rows={3}
          />
          <div className="flex items-center gap-3 mt-3">
            <button
              onClick={() => onReject(rejectFeedback, "script_generation")}
              disabled={loading || !rejectFeedback.trim()}
              className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-500 transition disabled:opacity-50"
            >
              Regenerate from Script
            </button>
            <button
              onClick={() => onReject(rejectFeedback, "hook_lab")}
              disabled={loading || !rejectFeedback.trim()}
              className="px-4 py-2 border border-red-500/30 text-red-400 rounded-lg text-sm font-medium hover:bg-red-500/10 transition disabled:opacity-50"
            >
              Regenerate from Hook
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
