"use client";

import { useState } from "react";
import { ContentAsset, WorkflowDetail } from "@/lib/api";
import { PLATFORM_LABELS } from "../types";
import { ContentPreview } from "./content-preview";
import { ExportBar } from "./export-bar";
import { TestReportPanel } from "./test-report";
import { VersionHistory } from "./version-history";

interface CompletedSectionProps {
  workflow: WorkflowDetail;
  assets: ContentAsset[];
}

export function CompletedSection({ workflow, assets }: CompletedSectionProps) {
  const platforms = workflow.platforms || ["youtube"];
  const [activeTab, setActiveTab] = useState(platforms[0]);

  const contentPack =
    (workflow.settings as any)?._content_pack ||
    (workflow.settings as any)?._edited_pack ||
    {};

  return (
    <div>
      <ExportBar workflowId={workflow.id} />

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

      <ContentPreview
        platform={activeTab}
        contentPack={contentPack}
        assets={assets}
      />

      {/* Version history */}
      <div className="mt-6">
        <VersionHistory workflowId={workflow.id} assets={assets} />
      </div>
    </div>
  );
}
