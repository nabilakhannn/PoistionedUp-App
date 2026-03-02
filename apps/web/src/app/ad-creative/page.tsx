"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/brand-context";
import { personalBrandsApi } from "@/lib/api/brand";
import { adCreativeApi, HOOK_TYPES, AD_PLATFORMS } from "@/lib/api/ad-creative";
import type { AdVariation, AdGenerateResponse } from "@/lib/api/ad-creative";
import type { BrandResearchSession } from "@/lib/api/brand";

// ── Icons ─────────────────────────────────────────────────

function ThumbUpIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 .75-.75 2.25 2.25 0 0 1 2.25 2.25c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282m0 0h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 0 1-2.649 7.521c-.388.482-.987.729-1.605.729H13.48c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 0 0-1.423-.23H5.904m10.598-9.75H14.25M5.904 18.5c.083.205.173.405.27.602.197.4-.078.898-.523.898h-.908c-.889 0-1.713-.518-1.972-1.368a12 12 0 0 1-.521-3.507c0-1.553.295-3.036.831-4.398C3.387 9.953 4.167 9.5 5 9.5h1.053c.472 0 .745.556.5.96a8.958 8.958 0 0 0-1.302 4.665c0 1.194.232 2.333.654 3.375Z" />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.498 15.25H4.372c-1.026 0-1.945-.694-2.054-1.715a12.137 12.137 0 0 1-.068-1.285c0-2.848.992-5.464 2.649-7.521C5.353 4.247 5.95 4 6.57 4h4.898c.482 0 .964.078 1.423.23l3.114 1.04a4.501 4.501 0 0 0 1.423.23h1.294M7.498 15.25c.618 0 .991.724.725 1.282A7.471 7.471 0 0 0 7.5 19.75 2.25 2.25 0 0 0 9.75 22a.75.75 0 0 0 .75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 0 0 2.86-2.4c.498-.634 1.226-1.08 2.032-1.08h.384m-10.253 1.5H9.7m8.075-9.75c.01.05.027.1.05.148.593 1.2.925 2.55.925 3.977 0 1.487-.36 2.89-.999 4.125m.023-8.25c-.076-.365.183-.75.575-.75h.908c.889 0 1.713.518 1.972 1.368.339 1.11.521 2.287.521 3.507 0 1.553-.295 3.036-.831 4.398-.306.774-1.086 1.227-1.918 1.227h-1.053c-.472 0-.745-.556-.5-.96a8.95 8.95 0 0 0 .303-.54" />
    </svg>
  );
}

function ChevronDownIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

// ── Skeleton ──────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="border border-border rounded-xl p-4 animate-pulse space-y-3">
      <div className="flex gap-2">
        <div className="h-5 w-20 bg-muted rounded-full" />
        <div className="h-5 w-16 bg-muted rounded-full" />
      </div>
      <div className="h-5 w-3/4 bg-muted rounded" />
      <div className="h-4 w-full bg-muted rounded" />
      <div className="h-4 w-5/6 bg-muted rounded" />
      <div className="flex gap-2 pt-1">
        <div className="h-7 w-24 bg-muted rounded-full" />
        <div className="h-7 w-20 bg-muted rounded-full" />
      </div>
    </div>
  );
}

// ── Variation Card ────────────────────────────────────────

interface VariationCardProps {
  variation: AdVariation;
  approved: boolean;
  dismissed: boolean;
  onApprove: () => void;
  onDismiss: () => void;
}

function VariationCard({ variation, approved, dismissed, onApprove, onDismiss }: VariationCardProps) {
  const platformColors: Record<string, string> = {
    facebook: "bg-blue-100 text-blue-700",
    instagram: "bg-pink-100 text-pink-700",
    linkedin: "bg-sky-100 text-sky-700",
  };

  return (
    <div
      className={`border rounded-xl p-4 transition-all ${
        approved
          ? "border-green-400 bg-green-50/50"
          : dismissed
          ? "border-border/30 bg-muted/30 opacity-50"
          : "border-border bg-card hover:border-primary/30"
      }`}
    >
      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
          Targets: {variation.hook_angle}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${platformColors[variation.platform] || "bg-muted text-muted-foreground"}`}>
          {variation.platform}
        </span>
      </div>

      {/* Headline */}
      <p className="font-semibold text-card-foreground text-sm mb-1.5">
        {variation.headline}
      </p>

      {/* Primary text */}
      <p className="text-sm text-muted-foreground mb-3 leading-relaxed">
        {variation.primary_text}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span className="text-xs px-2.5 py-1 rounded-full border border-border text-muted-foreground">
          {variation.cta}
        </span>
        <div className="flex gap-1.5">
          <button
            onClick={onApprove}
            title="Approve"
            className={`p-1.5 rounded-lg transition-colors ${
              approved
                ? "bg-green-500 text-white"
                : "hover:bg-green-100 text-muted-foreground hover:text-green-600"
            }`}
          >
            <ThumbUpIcon />
          </button>
          <button
            onClick={onDismiss}
            title="Dismiss"
            className={`p-1.5 rounded-lg transition-colors ${
              dismissed
                ? "bg-red-400 text-white"
                : "hover:bg-red-50 text-muted-foreground hover:text-red-500"
            }`}
          >
            <ThumbDownIcon />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Hook Section ──────────────────────────────────────────

interface HookSectionProps {
  hookType: string;
  label: string;
  variations: AdVariation[];
  approvedIds: Set<string>;
  dismissedIds: Set<string>;
  onApprove: (id: string) => void;
  onDismiss: (id: string) => void;
}

function HookSection({ hookType, label, variations, approvedIds, dismissedIds, onApprove, onDismiss }: HookSectionProps) {
  const [open, setOpen] = useState(true);
  const approvedCount = variations.filter(v => approvedIds.has(v.id)).length;

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-card hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-card-foreground text-sm">{label}</span>
          <span className="text-xs text-muted-foreground">{variations.length} variations</span>
          {approvedCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">
              {approvedCount} approved
            </span>
          )}
        </div>
        <ChevronDownIcon open={open} />
      </button>

      {open && (
        <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-3 bg-card/50">
          {variations.map((v) => (
            <VariationCard
              key={v.id}
              variation={v}
              approved={approvedIds.has(v.id)}
              dismissed={dismissedIds.has(v.id)}
              onApprove={() => onApprove(v.id)}
              onDismiss={() => onDismiss(v.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────

export default function AdCreativePage() {
  const { brands, currentBrand, brandId } = useBrand();

  // Controls
  const [sessions, setSessions] = useState<BrandResearchSession[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [selectedHookTypes, setSelectedHookTypes] = useState<string[]>(
    HOOK_TYPES.map(h => h.value)
  );
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(
    AD_PLATFORMS.map(p => p.value)
  );
  const [countPerHook, setCountPerHook] = useState(8);
  const [loadingSessions, setLoadingSessions] = useState(false);

  // Results
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AdGenerateResponse | null>(null);
  const [approvedIds, setApprovedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Staging
  const [staging, setStaging] = useState(false);
  const [stageSuccess, setStageSuccess] = useState("");

  // Load research sessions when brand changes
  useEffect(() => {
    if (!brandId) {
      setSessions([]);
      setSelectedSession("");
      return;
    }

    setLoadingSessions(true);
    personalBrandsApi
      .listResearch(brandId)
      .then((data: { sessions: BrandResearchSession[] }) => {
        const completed = (data.sessions || []).filter((s: BrandResearchSession) => s.status === "completed");
        setSessions(completed);
        setSelectedSession(completed[0]?.id || "");
      })
      .catch(() => setSessions([]))
      .finally(() => setLoadingSessions(false));
  }, [brandId]);

  const toggleHookType = (value: string) => {
    setSelectedHookTypes(prev =>
      prev.includes(value) ? prev.filter(h => h !== value) : [...prev, value]
    );
  };

  const togglePlatform = (value: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(value) ? prev.filter(p => p !== value) : [...prev, value]
    );
  };

  const handleApprove = (id: string) => {
    setApprovedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        // Un-dismiss if previously dismissed
        setDismissedIds(d => { const nd = new Set(d); nd.delete(id); return nd; });
      }
      return next;
    });
  };

  const handleDismiss = (id: string) => {
    setDismissedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        // Un-approve if previously approved
        setApprovedIds(a => { const na = new Set(a); na.delete(id); return na; });
      }
      return next;
    });
  };

  const handleGenerate = async () => {
    if (!brandId || !selectedSession) return;

    setGenerating(true);
    setError("");
    setResult(null);
    setApprovedIds(new Set());
    setDismissedIds(new Set());
    setStageSuccess("");

    try {
      const data = await adCreativeApi.generate(brandId, {
        session_id: selectedSession,
        hook_types: selectedHookTypes.length > 0 ? selectedHookTypes : undefined,
        platforms: selectedPlatforms.length > 0 ? selectedPlatforms : undefined,
        count_per_hook: countPerHook,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Generation failed. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleStage = async () => {
    if (!brandId || !result || approvedIds.size === 0) return;

    setStaging(true);
    setStageSuccess("");

    try {
      const stageResult = await adCreativeApi.stage(
        brandId,
        result.deliverable_id,
        Array.from(approvedIds)
      );
      setStageSuccess(
        `${stageResult.staged_count} ad${stageResult.staged_count !== 1 ? "s" : ""} staged to Composer as drafts.`
      );
    } catch (err: any) {
      setError(err.message || "Staging failed. Please try again.");
    } finally {
      setStaging(false);
    }
  };

  const totalVariations = result
    ? Object.values(result.variations_by_hook).reduce((sum, arr) => sum + arr.length, 0)
    : 0;

  const approvedCount = approvedIds.size;
  const expectedCount = selectedHookTypes.length * countPerHook;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Left Panel: Controls ── */}
      <aside className="w-72 flex-shrink-0 border-r border-border bg-card flex flex-col overflow-y-auto">
        <div className="p-5 border-b border-border">
          <h1 className="text-lg font-semibold text-card-foreground">Ad Creative</h1>
          <p className="text-xs text-muted-foreground mt-1">
            Generate {expectedCount}+ ad variations from your brand research
          </p>
        </div>

        <div className="p-5 space-y-6 flex-1">
          {/* Brand info */}
          {currentBrand && (
            <div className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
              <span className="font-medium text-card-foreground truncate">{currentBrand.name}</span>
            </div>
          )}

          {/* Research session selector */}
          <div>
            <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Research Session
            </label>
            {!brandId ? (
              <p className="text-xs text-muted-foreground">Select a brand first</p>
            ) : loadingSessions ? (
              <div className="h-9 bg-muted rounded-lg animate-pulse" />
            ) : sessions.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No completed research sessions found.{" "}
                <a href="/brands" className="text-primary hover:underline">
                  Run brand research first.
                </a>
              </p>
            ) : (
              <select
                value={selectedSession}
                onChange={e => setSelectedSession(e.target.value)}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-background text-card-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                {sessions.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.seed_input?.name || s.seed_input?.industry || "Session"} —{" "}
                    {new Date(s.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Hook types */}
          <div>
            <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Hook Types
            </label>
            <div className="space-y-1.5">
              {HOOK_TYPES.map(hook => (
                <label key={hook.value} className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selectedHookTypes.includes(hook.value)}
                    onChange={() => toggleHookType(hook.value)}
                    className="rounded border-border text-primary focus:ring-primary/30"
                  />
                  <span className="text-sm text-card-foreground group-hover:text-primary transition-colors">
                    {hook.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Platforms */}
          <div>
            <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Platforms
            </label>
            <div className="space-y-1.5">
              {AD_PLATFORMS.map(p => (
                <label key={p.value} className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selectedPlatforms.includes(p.value)}
                    onChange={() => togglePlatform(p.value)}
                    className="rounded border-border text-primary focus:ring-primary/30"
                  />
                  <span className="text-sm text-card-foreground group-hover:text-primary transition-colors">
                    {p.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Count per hook */}
          <div>
            <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Variations per Hook: <span className="text-primary">{countPerHook}</span>
            </label>
            <input
              type="range"
              min={4}
              max={8}
              value={countPerHook}
              onChange={e => setCountPerHook(Number(e.target.value))}
              className="w-full accent-primary"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>4</span>
              <span>8</span>
            </div>
          </div>
        </div>

        {/* Generate button */}
        <div className="p-5 border-t border-border">
          <button
            onClick={handleGenerate}
            disabled={generating || !brandId || !selectedSession || selectedHookTypes.length === 0}
            className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generating
              ? "Generating..."
              : `Generate ${expectedCount} Ad Variations`}
          </button>
          {generating && (
            <p className="text-xs text-muted-foreground text-center mt-2">
              ~20–40s · {selectedHookTypes.length} LLM calls
            </p>
          )}
        </div>
      </aside>

      {/* ── Right Panel: Results ── */}
      <main className="flex-1 overflow-y-auto bg-background relative">
        <div className="p-6 max-w-4xl mx-auto pb-24">

          {/* Error */}
          {error && (
            <div className="mb-4 p-4 rounded-xl border border-red-200 bg-red-50 text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Stage success */}
          {stageSuccess && (
            <div className="mb-4 p-4 rounded-xl border border-green-200 bg-green-50 text-green-700 text-sm">
              {stageSuccess}{" "}
              <a href="/composer" className="underline font-medium">
                View in Composer →
              </a>
            </div>
          )}

          {/* Loading skeleton */}
          {generating && (
            <div className="space-y-6">
              {selectedHookTypes.map(ht => (
                <div key={ht} className="border border-border rounded-xl overflow-hidden">
                  <div className="px-4 py-3 bg-card border-b border-border">
                    <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                  </div>
                  <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {Array.from({ length: Math.min(countPerHook, 4) }).map((_, i) => (
                      <SkeletonCard key={i} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {!generating && !result && !error && (
            <div className="flex flex-col items-center justify-center h-96 text-center">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-card-foreground mb-2">Ready to generate ads</h2>
              <p className="text-sm text-muted-foreground max-w-sm">
                Select a completed research session and click Generate to create{" "}
                {expectedCount}+ ad variations powered by your brand research.
              </p>
            </div>
          )}

          {/* Results */}
          {result && !generating && (
            <div className="space-y-5">
              {/* Summary header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-card-foreground">
                    {totalVariations} Variations Generated
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {result.brand_name} · {result.niche} · Approve variations to stage them
                  </p>
                </div>
                <button
                  onClick={handleGenerate}
                  className="text-xs px-3 py-1.5 border border-border rounded-lg text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors"
                >
                  Regenerate
                </button>
              </div>

              {/* Hook sections */}
              {HOOK_TYPES.filter(h => result.variations_by_hook[h.value]?.length > 0).map(hook => (
                <HookSection
                  key={hook.value}
                  hookType={hook.value}
                  label={hook.label}
                  variations={result.variations_by_hook[hook.value] || []}
                  approvedIds={approvedIds}
                  dismissedIds={dismissedIds}
                  onApprove={handleApprove}
                  onDismiss={handleDismiss}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Sticky Stage Footer ── */}
        {result && !generating && (
          <div className="fixed bottom-0 left-72 md:left-[33rem] right-0 bg-card border-t border-border px-6 py-4 flex items-center justify-between z-10">
            <div className="text-sm text-muted-foreground">
              {approvedCount > 0
                ? `${approvedCount} variation${approvedCount !== 1 ? "s" : ""} approved`
                : "Thumbs up variations to approve them"}
            </div>
            <button
              onClick={handleStage}
              disabled={staging || approvedCount === 0}
              className="px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {staging
                ? "Staging..."
                : `Stage ${approvedCount > 0 ? approvedCount : ""} Approved → Composer`}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
