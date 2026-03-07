"use client";

import Link from "next/link";
import { WorkflowInfo } from "@/lib/api/marketplace";

/* ── Category theming ── */

const CATEGORY_COLORS: Record<string, { gradient: string; border: string; label: string }> = {
  ads_funnels: {
    gradient: "from-orange-500/20 to-red-500/20",
    border: "border-orange-500/20",
    label: "Ads & Funnels",
  },
  content_marketing: {
    gradient: "from-violet-500/20 to-purple-600/20",
    border: "border-violet-500/20",
    label: "Content Marketing",
  },
  lead_gen: {
    gradient: "from-emerald-500/20 to-green-600/20",
    border: "border-emerald-500/20",
    label: "Lead Generation",
  },
  email_marketing: {
    gradient: "from-blue-500/20 to-cyan-500/20",
    border: "border-blue-500/20",
    label: "Email Marketing",
  },
  strategy: {
    gradient: "from-amber-500/20 to-yellow-500/20",
    border: "border-amber-500/20",
    label: "Strategy & Coaching",
  },
};

const DEFAULT_COLOR = {
  gradient: "from-zinc-700/20 to-zinc-800/20",
  border: "border-zinc-700/20",
  label: "Workflow",
};

/* ── Icon paths (keyed by icon name from backend registry) ── */

const ICON_PATHS: Record<string, string> = {
  rocket:
    "M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 0 0-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z",
  pencil:
    "m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10",
  users:
    "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
  envelope:
    "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
  lightbulb:
    "M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18",
};

/* ── Component ── */

export interface WorkflowCardProps {
  workflow: WorkflowInfo;
  usageCount?: number;
  href: string;
}

export function WorkflowCard({ workflow, usageCount = 0, href }: WorkflowCardProps) {
  const theme = CATEGORY_COLORS[workflow.category] ?? DEFAULT_COLOR;
  const iconPath = ICON_PATHS[workflow.icon] ?? ICON_PATHS.lightbulb;
  const isComingSoon = workflow.status === "coming_soon";

  const cardContent = (
    <div className="h-full flex flex-col gap-3">
      {/* Top row: icon + category + arrow */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Gradient icon box */}
          <div
            className={`w-9 h-9 shrink-0 rounded-xl bg-gradient-to-br ${theme.gradient} border ${theme.border} flex items-center justify-center`}
          >
            <svg className="w-4 h-4 text-zinc-200" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
            </svg>
          </div>
          <span className="text-[10px] font-medium text-zinc-500 truncate">{theme.label}</span>
        </div>
        <span className="text-zinc-600 shrink-0 mt-0.5">→</span>
      </div>

      {/* Title + description */}
      <div className="flex-1">
        <p className="text-sm font-semibold text-zinc-100 leading-snug mb-1">{workflow.name}</p>
        <p className="text-[11px] text-zinc-500 leading-relaxed line-clamp-2">{workflow.description}</p>
      </div>

      {/* Bottom row: tags + badge */}
      <div className="flex items-end justify-between gap-2">
        <div className="flex flex-wrap gap-1 min-w-0">
          {workflow.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-[9px] px-1.5 py-0.5 rounded-md bg-white/[0.04] ring-1 ring-white/[0.06] text-zinc-500 truncate"
            >
              {tag}
            </span>
          ))}
          {workflow.multi_step && workflow.steps.length > 0 && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-violet-500/10 ring-1 ring-violet-500/20 text-violet-400">
              {workflow.steps.length} steps
            </span>
          )}
          {workflow.engine === "manus_beneficial" && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-blue-500/10 ring-1 ring-blue-500/20 text-blue-400">
              Manus
            </span>
          )}
        </div>
        {isComingSoon ? (
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-zinc-800 ring-1 ring-white/[0.06] text-zinc-500 shrink-0 whitespace-nowrap">
            COMING SOON
          </span>
        ) : (
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20 text-emerald-400 shrink-0 whitespace-nowrap">
            ● ACTIVE
          </span>
        )}
      </div>

      {/* Usage count */}
      {usageCount > 0 && (
        <p className="text-[10px] text-zinc-600">
          Used {usageCount} time{usageCount === 1 ? "" : "s"}
        </p>
      )}
    </div>
  );

  if (isComingSoon) {
    return (
      <div
        className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.02] p-4 opacity-60 cursor-not-allowed"
        aria-disabled="true"
      >
        {cardContent}
      </div>
    );
  }

  return (
    <Link
      href={href}
      className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.03] p-4 flex flex-col transition-all duration-150 hover:ring-violet-500/20 hover:bg-white/[0.05] hover:-translate-y-px"
    >
      {cardContent}
    </Link>
  );
}
