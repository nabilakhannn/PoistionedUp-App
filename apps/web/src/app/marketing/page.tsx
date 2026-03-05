"use client";

/**
 * Marketing Room — Notion-style left sidebar layout (Slice 92d UX fix)
 * Left sidebar section list + full-page main content area.
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { ContentKanban } from "@/components/content-kanban";
import { ImageStudio } from "@/components/image-studio";
import { MarketingCalendar } from "@/components/marketing-calendar";
import { CompetitorIntelEmbed } from "@/components/competitor-intel-embed";
import { LandingPageStudio } from "@/components/landing-page-studio";

type Section = "content" | "calendar" | "ads" | "images" | "landing" | "competitors" | "strategy";

const SECTIONS: { key: Section; label: string; emoji: string; description: string }[] = [
  { key: "content", label: "Content", emoji: "📋", description: "Content pipeline & Kanban board" },
  { key: "calendar", label: "Calendar", emoji: "📅", description: "Month view — scheduled posts" },
  { key: "ads", label: "Ads", emoji: "🎯", description: "Ad creative engine — 40 variations" },
  { key: "images", label: "Images", emoji: "🖼️", description: "AI image generation studio" },
  { key: "landing", label: "Landing Pages", emoji: "🚀", description: "AI-generated pages from inspiration URLs" },
  { key: "competitors", label: "Competitors", emoji: "🕵️", description: "Threat scores & intel feed" },
  { key: "strategy", label: "Strategy", emoji: "🗺️", description: "Content pillars & monthly content plan" },
];

const PILLAR_EMOJIS = ["🌱", "⚡", "🔍", "⚙️", "🎯", "💡", "🚀", "🎨"];

export default function MarketingPage() {
  const [activeSection, setActiveSection] = useState<Section>("content");
  const { currentBrand } = useBrand();
  const [pillars, setPillars] = useState<string[]>([]);
  const [pillarsLoading, setPillarsLoading] = useState(false);

  useEffect(() => {
    if (activeSection !== "strategy" || !currentBrand?.id) return;
    setPillarsLoading(true);
    agentBridgeApi.getContext(currentBrand.id)
      .then((ctx) => {
        const raw = ctx.content_pillars ?? [];
        // Guard: pillars may be strings or {type, text} objects from LLM responses
        const safe = raw.map((p: unknown) =>
          typeof p === "string" ? p : (p as { text?: string })?.text ?? String(p)
        );
        setPillars(safe);
      })
      .catch(() => setPillars([]))
      .finally(() => setPillarsLoading(false));
  }, [activeSection, currentBrand?.id]);

  const current = SECTIONS.find((s) => s.key === activeSection)!;

  return (
    <div className="flex min-h-screen bg-background">
      {/* ── Left Sidebar ─────────────────────────────────── */}
      <aside className="w-52 flex-shrink-0 border-r border-border bg-card/30">
        <div className="px-3 pt-5 pb-4">
          {/* Room title */}
          <div className="px-2 mb-4">
            <h1 className="text-sm font-bold text-foreground flex items-center gap-2">
              📣 Create
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

          {/* ── LANDING PAGES ─────────────────────────── */}
          {activeSection === "landing" && (
            currentBrand ? (
              <LandingPageStudio brandId={currentBrand.id} />
            ) : (
              <NoBrand icon="🚀" />
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

          {/* ── STRATEGY ──────────────────────────────── */}
          {activeSection === "strategy" && (
            currentBrand ? (
              <div className="space-y-6">
                {/* Content Pillars */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <div className="flex items-start justify-between mb-5">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">Content Pillars</h3>
                      <p className="text-xs text-muted-foreground mt-1">
                        The 5 core themes every piece of content should map to. Derived from your brand profile.
                      </p>
                    </div>
                    <Link
                      href={`/brands/${currentBrand.id}`}
                      className="text-xs text-primary hover:underline flex-shrink-0 ml-4"
                    >
                      Edit brand profile →
                    </Link>
                  </div>
                  {pillarsLoading ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className="rounded-lg border border-border bg-card/30 p-4 h-20 animate-pulse" />
                      ))}
                    </div>
                  ) : pillars.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {pillars.map((pillar, i) => (
                        <div key={i} className="rounded-lg border border-border bg-card/50 p-4">
                          <div className="text-lg mb-2">{PILLAR_EMOJIS[i % PILLAR_EMOJIS.length]}</div>
                          <div className="text-sm font-medium text-foreground">{pillar}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-border bg-card/20 px-6 py-8 text-center">
                      <div className="text-2xl mb-2">✨</div>
                      <p className="text-sm text-muted-foreground mb-3">
                        No content pillars yet. Generate them from your brand profile.
                      </p>
                      <Link
                        href={`/brands/${currentBrand.id}`}
                        className="inline-flex items-center gap-1.5 text-xs bg-primary text-primary-foreground px-4 py-2 rounded-lg font-medium hover:opacity-90 transition"
                      >
                        Generate from Brand Profile →
                      </Link>
                    </div>
                  )}
                </div>

                {/* Monthly Focus */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <h3 className="text-sm font-semibold text-foreground mb-1">This Month&apos;s Focus</h3>
                  <p className="text-xs text-muted-foreground mb-4">
                    Use your content calendar and competitor intel to plan what to write this month.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setActiveSection("calendar")}
                      className="text-xs bg-primary/10 text-primary border border-primary/20 px-3 py-1.5 rounded-lg font-medium hover:bg-primary/20 transition"
                    >
                      📅 Open Calendar
                    </button>
                    <Link
                      href="/mission-control/analytics"
                      className="text-xs bg-card border border-border px-3 py-1.5 rounded-lg font-medium text-muted-foreground hover:text-foreground hover:border-border/80 transition"
                    >
                      📊 View Analytics
                    </Link>
                    <Link
                      href="/sales?tab=icp"
                      className="text-xs bg-card border border-border px-3 py-1.5 rounded-lg font-medium text-muted-foreground hover:text-foreground hover:border-border/80 transition"
                    >
                      🎯 ICP Research
                    </Link>
                  </div>
                </div>
              </div>
            ) : (
              <NoBrand icon="🗺️" />
            )
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
