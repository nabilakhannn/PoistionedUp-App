"use client";

/**
 * GettingStartedChecklist — Slice 107
 *
 * 6-step progressive onboarding checklist shown at the top of Today page.
 * Dismissible via localStorage. Auto-hides when >= 5 steps are done.
 */

import { useState } from "react";
import Link from "next/link";
import type { PersonalBrandSummary } from "@/lib/api/brand";
import type { Deliverable } from "@/lib/api/mission-control";

interface Step {
  label: string;
  done: boolean;
  href: string;
  cta: string;
}

interface GettingStartedChecklistProps {
  currentBrand: PersonalBrandSummary | null;
  deliverables: Deliverable[];
}

const LS_KEY = "getting_started_dismissed";

export function GettingStartedChecklist({
  currentBrand,
  deliverables,
}: GettingStartedChecklistProps) {
  const [dismissed, setDismissed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(LS_KEY) === "true";
  });

  if (dismissed) return null;

  const hasApproved = deliverables.some((d) => d.status === "approved");
  const hasVisitedContent = typeof window !== "undefined" && localStorage.getItem("visited_content_room") === "true";

  const steps: Step[] = [
    { label: "Created account", done: true, href: "#", cta: "" },
    { label: "Set up a brand", done: !!currentBrand, href: "/onboarding", cta: "Create brand" },
    { label: "Build your brand voice", done: Object.keys(currentBrand?.completeness ?? {}).length > 0, href: currentBrand ? `/brands/${currentBrand.id}` : "/brands", cta: "Open brand" },
    { label: "Generate your first post", done: deliverables.length > 0, href: "/mission-control", cta: "Run pipeline" },
    { label: "Review & approve a post", done: hasApproved, href: "/mission-control", cta: "Review posts" },
    { label: "Explore Create room", done: hasVisitedContent, href: "/content", cta: "Go to Create" },
  ];

  const completedCount = steps.filter((s) => s.done).length;

  // Auto-hide when almost done (5+ of 6)
  if (completedCount >= 5) return null;

  const pct = Math.round((completedCount / steps.length) * 100);

  const handleDismiss = () => {
    localStorage.setItem(LS_KEY, "true");
    setDismissed(true);
  };

  return (
    <div
      data-testid="getting-started-checklist"
      className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 space-y-3"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">Getting Started</span>
          <span className="text-xs text-muted-foreground">
            {completedCount}/{steps.length}
          </span>
        </div>
        <button
          onClick={handleDismiss}
          className="text-[10px] text-muted-foreground hover:text-foreground transition"
        >
          Dismiss
        </button>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-green-400 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-1.5">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <span
              className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] shrink-0 ${
                step.done
                  ? "bg-green-500/20 text-green-400"
                  : "bg-muted/30 text-muted-foreground"
              }`}
            >
              {step.done ? "✓" : i + 1}
            </span>
            <span
              className={`text-xs flex-1 ${
                step.done ? "text-muted-foreground line-through" : "text-foreground font-medium"
              }`}
            >
              {step.label}
            </span>
            {!step.done && step.cta && (
              <Link
                href={step.href}
                className="text-[10px] text-primary hover:underline shrink-0"
              >
                {step.cta} →
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
