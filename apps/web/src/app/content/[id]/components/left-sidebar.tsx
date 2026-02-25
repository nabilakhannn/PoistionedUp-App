"use client";

import { useState } from "react";
import { WorkflowDetail, ContentAsset, StepSnapshot } from "@/lib/api";
import { PipelineStepper } from "./pipeline-stepper";
import { TestReportPanel } from "./test-report";
import { ExportBar } from "./export-bar";
import { VersionHistory } from "./version-history";

type SidebarSection =
  | "pipeline"
  | "context"
  | "insights"
  | "tools"
  | "export"
  | null;

interface LeftSidebarProps {
  workflow: WorkflowDetail;
  assets: ContentAsset[];
  snapshots?: StepSnapshot[];
  onRefresh: () => void;
}

export function LeftSidebar({ workflow, assets, snapshots = [], onRefresh }: LeftSidebarProps) {
  const [openSection, setOpenSection] =
    useState<SidebarSection>("pipeline");

  const toggleSection = (section: SidebarSection) => {
    setOpenSection(openSection === section ? null : section);
  };

  const isComplete =
    workflow.status === "completed" || workflow.status === "approved";

  return (
    <div className="space-y-1">
      {/* PIPELINE */}
      <SidebarPanel
        icon="📊"
        label="Pipeline"
        open={openSection === "pipeline"}
        onClick={() => toggleSection("pipeline")}
      >
        <PipelineStepper
          currentStep={workflow.current_step}
          status={workflow.status}
          snapshots={snapshots}
        />
      </SidebarPanel>

      {/* CONTEXT */}
      <SidebarPanel
        icon="🧠"
        label="Context"
        open={openSection === "context"}
        onClick={() => toggleSection("context")}
      >
        <div className="space-y-2">
          <ContextRow
            icon="🧠"
            label="Brand"
            value={
              (workflow.settings as any)?.brand_id
                ? "Connected"
                : "No brand"
            }
            connected={!!(workflow.settings as any)?.brand_id}
          />
          <ContextRow
            icon="📗"
            label="Knowledge"
            value={`${
              (workflow.settings as any)?.resource_count || 0
            } resources`}
          />
          <ContextRow
            icon="💡"
            label="Inspo"
            value={`${(workflow.settings as any)?.inspo_count || 0} items`}
          />
          <ContextRow
            icon="📝"
            label="Format"
            value={workflow.content_type || "youtube_long"}
          />
          <ContextRow
            icon="🎯"
            label="Objective"
            value={
              (workflow.settings as any)?.objective || "personal_branding"
            }
          />
          {(workflow.platforms || []).length > 0 && (
            <ContextRow
              icon="📺"
              label="Platforms"
              value={(workflow.platforms || []).join(", ")}
            />
          )}
        </div>
      </SidebarPanel>

      {/* INSIGHTS */}
      <SidebarPanel
        icon="📈"
        label="Insights"
        open={openSection === "insights"}
        onClick={() => toggleSection("insights")}
      >
        <div className="space-y-2 text-xs">
          <InsightRow
            label="Pipeline Steps"
            value={`${snapshots.length} completed`}
            active={snapshots.length > 0}
          />
          <InsightRow
            label="Performance"
            value="Patterns feeding pipeline"
            active
          />
          <InsightRow
            label="Memory"
            value="Agent learning from history"
            active
          />
          <InsightRow
            label="Experiments"
            value="A/B testing active"
          />
          <InsightRow
            label="Voice DNA"
            value="Style consistency checked"
            active
          />
          {(workflow.settings as any)?._test_report && (
            <InsightRow
              label="Quality Gate"
              value={
                (workflow.settings as any)._test_report.overall_pass
                  ? "Passed"
                  : "Flagged"
              }
              active={(workflow.settings as any)._test_report.overall_pass}
            />
          )}
        </div>
      </SidebarPanel>

      {/* TOOLS */}
      <SidebarPanel
        icon="🔧"
        label="Tools"
        open={openSection === "tools"}
        onClick={() => toggleSection("tools")}
      >
        <div className="space-y-3">
          <TestReportPanel workflow={workflow} />
          <VersionHistory
            workflowId={workflow.id}
            assets={assets}
            onRestore={onRefresh}
          />
        </div>
      </SidebarPanel>

      {/* EXPORT */}
      {isComplete && (
        <SidebarPanel
          icon="📤"
          label="Export"
          open={openSection === "export"}
          onClick={() => toggleSection("export")}
        >
          <ExportBar workflowId={workflow.id} compact />
        </SidebarPanel>
      )}
    </div>
  );
}

// ── Sub-components ──

function SidebarPanel({
  icon,
  label,
  open,
  onClick,
  children,
}: {
  icon: string;
  label: string;
  open: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-zinc-800/50 rounded-lg overflow-hidden">
      <button
        onClick={onClick}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-zinc-800/50 transition-colors"
      >
        <span className="text-sm">{icon}</span>
        <span className="text-sm font-medium text-zinc-300 flex-1">
          {label}
        </span>
        <span className="text-zinc-600 text-xs">
          {open ? "▼" : "▶"}
        </span>
      </button>
      {open && <div className="px-3 pb-3 pt-1">{children}</div>}
    </div>
  );
}

function ContextRow({
  icon,
  label,
  value,
  connected,
}: {
  icon: string;
  label: string;
  value: string;
  connected?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs">{icon}</span>
      <span className="text-xs text-zinc-400 flex-1">{label}</span>
      <span
        className={`text-xs ${
          connected === false ? "text-zinc-600" : "text-zinc-300"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function InsightRow({
  label,
  value,
  active,
}: {
  label: string;
  value: string;
  active?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
          active ? "bg-green-400" : "bg-zinc-700"
        }`}
      />
      <span className="text-xs text-zinc-400 flex-1">{label}</span>
      <span className={`text-xs ${active ? "text-zinc-300" : "text-zinc-600"}`}>
        {value}
      </span>
    </div>
  );
}
