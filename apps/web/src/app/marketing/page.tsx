"use client";

/**
 * Marketing Room — Notion-style left sidebar layout (Slice 92d UX fix)
 * Left sidebar section list + full-page main content area.
 */

import { useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { ContentKanban } from "@/components/content-kanban";
import { ImageStudio } from "@/components/image-studio";
import { MarketingCalendar } from "@/components/marketing-calendar";
import { CompetitorIntelEmbed } from "@/components/competitor-intel-embed";

type Section = "content" | "calendar" | "ads" | "images" | "competitors" | "analytics";

const SECTIONS: { key: Section; label: string; emoji: string; description: string }[] = [
  { key: "content", label: "Content", emoji: "📋", description: "Content pipeline & Kanban board" },
  { key: "calendar", label: "Calendar", emoji: "📅", description: "Month view — scheduled posts" },
  { key: "ads", label: "Ads", emoji: "🎯", description: "Ad creative engine — 40 variations" },
  { key: "images", label: "Images", emoji: "🖼️", description: "AI image generation studio" },
  { key: "competitors", label: "Competitors", emoji: "🕵️", description: "Threat scores & intel feed" },
  { key: "analytics", label: "Analytics", emoji: "📊", description: "Voice DNA, QA tiers, performance" },
];

export default function MarketingPage() {
  const [activeSection, setActiveSection] = useState<Section>("content");
  const { currentBrand } = useBrand();

  const current = SECTIONS.find((s) => s.key === activeSection)!;

  return (
    <div className="flex min-h-screen bg-background">
      {/* ── Left Sidebar ─────────────────────────────────── */}
      <aside className="w-52 flex-shrink-0 border-r border-border bg-card/30">
        <div className="px-3 pt-5 pb-4">
          {/* Room title */}
          <div className="px-2 mb-4">
            <h1 className="text-sm font-bold text-foreground flex items-center gap-2">
              📣 Marketing
            </h1>
            {currentBrand && (
              <span className="text-[10px] text-muted-foreground truncate block mt-0.5">
                {currentBrand.name}
              </span>
            )}
          </div>

          {/* Section list */}
          <p className="text-[9px] text-muted-foreground uppercase tracking-wider px-2 mb-1.5">
            Sections
          </p>
          <nav className="space-y-0.5">
            {SECTIONS.map((section) => (
              <button
                key={section.key}
                onClick={() => setActiveSection(section.key)}
                className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-left transition-colors ${
                  activeSection === section.key
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                <span className="text-sm leading-none">{section.emoji}</span>
                <span className="text-sm font-medium">{section.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────── */}
      <main className="flex-1 overflow-auto">
        {/* Page header */}
        <div className="border-b border-border bg-card/20 px-6 py-4">
          <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
            <span>{current.emoji}</span> {current.label}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">{current.description}</p>
        </div>

        <div className="px-6 py-6">

          {/* ── CONTENT (Kanban) ───────────────────────── */}
          {activeSection === "content" && (
            currentBrand ? (
              <ContentKanban brandId={currentBrand.id} />
            ) : (
              <NoBrand icon="📋" />
            )
          )}

          {/* ── CALENDAR ──────────────────────────────── */}
          {activeSection === "calendar" && (
            currentBrand ? (
              <MarketingCalendar brandId={currentBrand.id} />
            ) : (
              <NoBrand icon="📅" />
            )
          )}

          {/* ── ADS ───────────────────────────────────── */}
          {activeSection === "ads" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  5 hook types × 8 formats = 40 variations per run.
                </p>
                <Link
                  href="/ad-creative"
                  className="text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium hover:opacity-90 transition"
                >
                  Generate 40 Variations →
                </Link>
              </div>

              <div className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-lg">
                    🎯
                  </div>
                  <div>
                    <div className="text-sm font-semibold">Text Ad Variations</div>
                    <div className="text-xs text-muted-foreground">
                      Pain / Outcome / Objection / Social Proof / Curiosity hooks
                    </div>
                  </div>
                </div>
                <Link href="/ad-creative" className="text-xs text-primary hover:underline">
                  Open Ad Creative Engine →
                </Link>
              </div>

              <div className="rounded-xl border border-border/50 bg-card/30 p-5 opacity-60">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-lg">
                    🎬
                  </div>
                  <div>
                    <div className="text-sm font-semibold">UGC Video Ads</div>
                    <div className="text-xs text-muted-foreground">
                      Sora / HeyGen / Runway → 15s + 30s → Meta Ads
                    </div>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground/60">Coming soon</span>
              </div>
            </div>
          )}

          {/* ── IMAGES ────────────────────────────────── */}
          {activeSection === "images" && (
            currentBrand ? (
              <ImageStudio brandId={currentBrand.id} />
            ) : (
              <NoBrand icon="🖼️" />
            )
          )}

          {/* ── COMPETITORS ───────────────────────────── */}
          {activeSection === "competitors" && (
            currentBrand ? (
              <CompetitorIntelEmbed brandId={currentBrand.id} />
            ) : (
              <NoBrand icon="🕵️" />
            )
          )}

          {/* ── ANALYTICS ─────────────────────────────── */}
          {activeSection === "analytics" && (
            <div className="rounded-xl border border-border bg-card/50 p-5">
              <p className="text-sm text-muted-foreground">
                Your full analytics dashboard is at{" "}
                <Link href="/mission-control/analytics" className="text-primary hover:underline">
                  Mission Control → Analytics
                </Link>
                .
              </p>
              <Link
                href="/mission-control/analytics"
                className="inline-block mt-3 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium hover:opacity-90 transition"
              >
                Open Analytics →
              </Link>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

function NoBrand({ icon }: { icon: string }) {
  return (
    <div className="rounded-xl border border-border bg-card/30 px-6 py-12 text-center">
      <div className="text-3xl mb-3">{icon}</div>
      <p className="text-sm font-medium text-foreground mb-1">No brand selected</p>
      <p className="text-xs text-muted-foreground mb-4">
        Select a brand from the sidebar to continue.
      </p>
      <Link href="/brands" className="text-xs text-primary hover:underline">
        Manage brands →
      </Link>
    </div>
  );
}
