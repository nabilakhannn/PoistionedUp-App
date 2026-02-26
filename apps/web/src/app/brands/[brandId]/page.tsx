"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  personalBrandsApi,
  PersonalBrandDetail,
  BrandCompleteness,
  ModelTierInfo,
  ModelTierListResponse,
} from "../../../lib/api";
import { useBrand } from "@/lib/brand-context";
import { ResearchPanel } from "./components/research-panel";

interface Stage {
  number: number;
  key: string;
  title: string;
  question: string;
  description: string;
  percentKey: keyof BrandCompleteness | null;
  ready: boolean;
}

const stages: Stage[] = [
  {
    number: 1,
    key: "foundation",
    title: "Foundation",
    question: "Who are you?",
    description:
      "Your beliefs, IT factor, achievements, stories, and content pillars. This is where your brand starts.",
    percentKey: "foundation_percent",
    ready: true,
  },
  {
    number: 2,
    key: "ica",
    title: "Ideal Client Avatar",
    question: "Who do you serve?",
    description:
      "Define your dream client: demographics, motivations, pains, desires, and fears.",
    percentKey: "ica_percent",
    ready: true,
  },
  {
    number: 3,
    key: "offer",
    title: "Your Offer",
    question: "What do you sell?",
    description:
      "Craft your offer: outcome, timeline, pricing, framework, and objections.",
    percentKey: "offer_percent",
    ready: true,
  },
  {
    number: 4,
    key: "brand",
    title: "Brand Statement",
    question: "How do you position yourself?",
    description:
      "Your positioning statement, unfair advantage leverage, and content pillars.",
    percentKey: "brand_percent",
    ready: true,
  },
  {
    number: 5,
    key: "authority",
    title: "Authority Building",
    question: "How do you build trust?",
    description:
      "Your credentials, certifications, case studies, testimonials, media features, and social proof.",
    percentKey: "authority_percent",
    ready: true,
  },
  {
    number: 6,
    key: "messaging",
    title: "Messaging",
    question: "What do you say and how?",
    description:
      "Key phrases, talking points, content themes, brand voice, and signature expressions.",
    percentKey: "messaging_percent",
    ready: true,
  },
  {
    number: 7,
    key: "positioning",
    title: "Positioning",
    question: "Where do you stand in the market?",
    description:
      "Market position, competitive angle, category design, and your unique wedge.",
    percentKey: "positioning_percent",
    ready: true,
  },
  {
    number: 8,
    key: "competitors",
    title: "Competitors",
    question: "Who else is playing and how are you different?",
    description:
      "Competitor analysis, differentiation strategy, white space opportunities, and your unique edge.",
    percentKey: "competitors_percent",
    ready: true,
  },
];

export default function BrandBuilderPage() {
  const params = useParams();
  const brandId = params.brandId as string;
  const { selectBrand } = useBrand();

  const [brand, setBrand] = useState<PersonalBrandDetail | null>(null);
  const [completeness, setCompleteness] = useState<BrandCompleteness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tierData, setTierData] = useState<ModelTierListResponse | null>(null);
  const [tierSaving, setTierSaving] = useState(false);
  const [showTierPicker, setShowTierPicker] = useState(false);

  useEffect(() => {
    if (brandId) {
      selectBrand(brandId);
    }
  }, [brandId, selectBrand]);

  useEffect(() => {
    if (!brandId) return;

    setLoading(true);
    Promise.all([
      personalBrandsApi.get(brandId),
      personalBrandsApi.getCompleteness(brandId),
      personalBrandsApi.getModelTiers(brandId).catch(() => null),
    ])
      .then(([brandData, comp, tiers]) => {
        setBrand(brandData);
        setCompleteness(comp);
        if (tiers) setTierData(tiers);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [brandId]);

  const handleTierChange = async (tierKey: string) => {
    if (!brandId || tierSaving) return;
    setTierSaving(true);
    try {
      const updated = await personalBrandsApi.updateModelTier(brandId, tierKey);
      setBrand(updated);
      setTierData((prev) => prev ? { ...prev, current_tier: tierKey } : prev);
      setShowTierPicker(false);
    } catch (e: any) {
      setError(e.message || "Failed to update model tier");
    } finally {
      setTierSaving(false);
    }
  };

  const refreshCompleteness = () => {
    if (!brandId) return;
    personalBrandsApi.getCompleteness(brandId).then(setCompleteness).catch(() => {});
  };

  const tierColors: Record<string, { bg: string; border: string; text: string; badge: string; icon: string }> = {
    budget: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-400", badge: "bg-green-500/20 text-green-400", icon: "text-green-400" },
    standard: { bg: "bg-primary/10", border: "border-primary/30", text: "text-primary", badge: "bg-primary/20 text-primary", icon: "text-primary" },
    premium: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400", badge: "bg-purple-500/20 text-purple-400", icon: "text-purple-400" },
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-background text-card-foreground">
        <div className="max-w-4xl mx-auto p-8">
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        </div>
      </main>
    );
  }

  const overallPercent = completeness?.overall_percent ?? 0;

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      <div className="max-w-4xl mx-auto p-8">
        <Link
          href="/brands"
          className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 mb-6 transition"
        >
          ← All brands
        </Link>

        <div className="flex items-start justify-between mb-2">
          <div>
            <h1 className="text-3xl font-bold text-card-foreground">{brand?.name || "Brand"}</h1>
            {brand?.description && (
              <p className="text-muted-foreground mt-1">{brand.description}</p>
            )}
          </div>
          <Link
            href={`/brands/${brandId}/settings`}
            className="px-3 py-1.5 border border-border text-muted-foreground rounded-lg text-sm hover:bg-accent hover:text-foreground transition"
          >
            Settings
          </Link>
        </div>

        <p className="text-muted-foreground mb-8">
          Build your brand step by step. Complete each stage in order.
        </p>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-300 text-sm">
            {error}
          </div>
        )}

        {completeness && (
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-sm font-medium text-foreground">
                Overall progress
              </span>
              <span className="text-sm text-muted-foreground">{overallPercent}%</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all"
                style={{ width: `${overallPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* Model Tier Selector */}
        {tierData && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <span className="text-sm font-medium text-foreground">AI Model Tier</span>
              </div>
              <button
                onClick={() => setShowTierPicker(!showTierPicker)}
                className="text-xs text-primary hover:text-primary/80 transition"
              >
                {showTierPicker ? "Close" : "Change"}
              </button>
            </div>

            {/* Current tier badge */}
            {!showTierPicker && (() => {
              const current = tierData.tiers.find((t) => t.key === tierData.current_tier);
              const colors = tierColors[tierData.current_tier] || tierColors.budget;
              return current ? (
                <div className={`flex items-center justify-between rounded-lg border p-3 ${colors.bg} ${colors.border}`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colors.bg}`}>
                      {tierData.current_tier === "budget" && (
                        <svg xmlns="http://www.w3.org/2000/svg" className={`w-4 h-4 ${colors.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                      )}
                      {tierData.current_tier === "standard" && (
                        <svg xmlns="http://www.w3.org/2000/svg" className={`w-4 h-4 ${colors.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                      )}
                      {tierData.current_tier === "premium" && (
                        <svg xmlns="http://www.w3.org/2000/svg" className={`w-4 h-4 ${colors.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>
                      )}
                    </div>
                    <div>
                      <span className={`text-sm font-medium ${colors.text}`}>{current.label}</span>
                      <p className="text-xs text-muted-foreground">{current.provider} &middot; ~{current.est_cost_per_chat_msg}/msg</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${colors.badge}`}>Active</span>
                </div>
              ) : null;
            })()}

            {/* Expanded tier picker */}
            {showTierPicker && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {tierData.tiers.map((tier) => {
                  const isActive = tierData.current_tier === tier.key;
                  const colors = tierColors[tier.key] || tierColors.budget;
                  return (
                    <button
                      key={tier.key}
                      onClick={() => handleTierChange(tier.key)}
                      disabled={tierSaving || isActive}
                      className={`relative rounded-xl border p-4 text-left transition-all ${
                        isActive
                          ? `${colors.border} ${colors.bg} ring-1 ring-offset-0 ${tier.key === "budget" ? "ring-green-500/40" : tier.key === "standard" ? "ring-primary/40" : "ring-purple-500/40"}`
                          : "border-border bg-card hover:border-border hover:bg-accent/50"
                      } ${tierSaving ? "opacity-50 cursor-wait" : isActive ? "cursor-default" : "cursor-pointer"}`}
                    >
                      {isActive && (
                        <div className={`absolute top-2 right-2 w-2 h-2 rounded-full ${tier.key === "budget" ? "bg-green-400" : tier.key === "standard" ? "bg-primary" : "bg-purple-400"}`} />
                      )}
                      <div className="mb-2">
                        <span className={`text-sm font-semibold ${isActive ? colors.text : "text-foreground"}`}>{tier.label}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mb-3 leading-relaxed">{tier.description}</p>
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Per message</span>
                          <span className={isActive ? colors.text : "text-foreground"}>{tier.est_cost_per_chat_msg}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Per workflow</span>
                          <span className={isActive ? colors.text : "text-foreground"}>{tier.est_cost_per_workflow}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Provider</span>
                          <span className="text-muted-foreground">{tier.provider}</span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Brand Strategist CTA */}
        <div className="mb-8">
          <Link
            href={`/brands/${brandId}/strategist`}
            className="block rounded-xl border-2 border-primary/30 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent hover:border-primary/50 hover:from-primary/15 transition-all group p-5"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center text-primary group-hover:bg-primary/30 transition flex-shrink-0">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-lg font-bold text-card-foreground group-hover:text-primary/80 transition">
                    AI Brand Strategist
                  </h2>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    One intelligent conversation to build your entire brand DNA. The AI guides you with option cards, refines your answers, and saves everything automatically.
                  </p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-full">Recommended</span>
                    <span className="text-xs text-muted-foreground">All 8 modules in one flow</span>
                  </div>
                </div>
              </div>
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-muted-foreground group-hover:text-primary transition flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </Link>
        </div>

        {/* AI Research Pipeline */}
        <div className="mb-8">
          <ResearchPanel
            brandId={brandId}
            brandName={brand?.name || ""}
            brandDescription={brand?.description || ""}
            onResearchApplied={refreshCompleteness}
          />
        </div>

        {/* Or: Module-by-Module */}
        <div className="flex items-center gap-3 mb-4">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-muted-foreground uppercase tracking-wider">Or build module by module</span>
          <div className="h-px flex-1 bg-border" />
        </div>

        {/* Learning Path */}
        <div className="relative">
          {/* Vertical connector line */}
          <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-border" />

          <div className="space-y-4">
            {stages.map((stage) => {
              const pct =
                stage.percentKey && completeness
                  ? completeness[stage.percentKey]
                  : 0;
              const isComplete = pct >= 80;
              const isStarted = pct > 0;

              const chatPath = stage.ready
                ? `/brands/${brandId}/chat/${stage.key}`
                : null;

              return (
                <div key={stage.key} className="relative flex gap-4">
                  {/* Stage number circle */}
                  <div
                    className={`relative z-10 flex items-center justify-center w-12 h-12 rounded-full border-2 text-sm font-bold shrink-0 ${
                      isComplete
                        ? "bg-green-600 border-green-600 text-white"
                        : isStarted
                        ? "bg-yellow-500/20 border-yellow-500 text-yellow-400"
                        : stage.ready
                        ? "bg-card border-border text-muted-foreground"
                        : "bg-card border-border text-muted-foreground"
                    }`}
                  >
                    {isComplete ? (
                      <svg
                        className="w-5 h-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    ) : (
                      stage.number
                    )}
                  </div>

                  {/* Stage card */}
                  <div
                    className={`flex-1 rounded-xl border p-5 ${
                      stage.ready
                        ? "bg-card border-border"
                        : "bg-card/50 border-border/50"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-lg font-semibold text-card-foreground">{stage.title}</h2>
                          {!stage.ready && (
                            <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded">
                              Coming soon
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-primary font-medium">
                          {stage.question}
                        </p>
                      </div>
                      {stage.ready && completeness && stage.percentKey && (
                        <span
                          className={`text-sm font-medium px-2 py-1 rounded ${
                            isComplete
                              ? "bg-green-500/20 text-green-400"
                              : isStarted
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {pct}%
                        </span>
                      )}
                    </div>

                    <p className="text-muted-foreground text-sm mb-3">
                      {stage.description}
                    </p>

                    {stage.ready && stage.percentKey && completeness && (
                      <div className="w-full bg-muted rounded-full h-1.5 mb-4">
                        <div
                          className={`h-1.5 rounded-full transition-all ${
                            isComplete
                              ? "bg-green-500"
                              : isStarted
                              ? "bg-yellow-500"
                              : "bg-border"
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    )}

                    {stage.ready && (
                      <div className="flex gap-3">
                        {chatPath && (
                          <Link
                            href={chatPath}
                            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
                          >
                            {isStarted ? "Continue chat" : "Start with AI"}
                          </Link>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </main>
  );
}
