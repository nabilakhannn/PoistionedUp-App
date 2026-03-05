"use client";

import { useState } from "react";
import { ContentAsset, WorkflowDetail } from "@/lib/api";
import { PLATFORM_LABELS } from "../types";
import { ContentPreview } from "./content-preview";

const PLATFORM_ICONS: Record<string, string> = {
  youtube: "📺",
  linkedin: "💼",
  twitter: "🐦",
  short_form: "📱",
};

interface RightPreviewProps {
  workflow: WorkflowDetail;
  assets: ContentAsset[];
}

export function RightPreview({ workflow, assets }: RightPreviewProps) {
  const platforms = workflow.platforms || ["youtube"];
  const [activeTab, setActiveTab] = useState(platforms[0]);
  const contentPack =
    (workflow.settings as any)?._content_pack ||
    (workflow.settings as any)?._edited_pack ||
    {};
  const isReady =
    workflow.status === "awaiting_approval" ||
    workflow.status === "completed" ||
    workflow.status === "approved";

  if (!isReady) {
    return (
      <div className="text-center py-12">
        <div className="text-3xl mb-3">👀</div>
        <p className="text-zinc-500 text-sm">
          Preview will appear here once content is generated.
        </p>
        <p className="text-zinc-600 text-xs mt-1">
          Currently:{" "}
          {workflow.status === "running"
            ? "pipeline running..."
            : workflow.status}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Platform tab bar */}
      <div className="flex border-b border-zinc-800">
        {platforms.map((p) => (
          <button
            key={p}
            onClick={() => setActiveTab(p)}
            className={`flex items-center gap-1 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === p
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            <span>{PLATFORM_ICONS[p] || "📄"}</span>
            <span>{PLATFORM_LABELS[p] || p}</span>
          </button>
        ))}
      </div>

      {/* Preview content */}
      <ContentPreview
        platform={activeTab}
        contentPack={contentPack}
        assets={assets}
      />
    </div>
  );
}
