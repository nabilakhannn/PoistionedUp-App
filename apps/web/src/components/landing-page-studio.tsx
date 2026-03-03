"use client";

/**
 * Landing Page Studio — Slice 93
 *
 * Two-phase AI landing page generator:
 *   Phase 1: Claude Haiku blueprints the structure (near-free)
 *   Phase 2: Claude Sonnet 4.6 writes the full self-contained HTML
 *
 * Features:
 *  - Optional inspiration URL (agent analyzes and clones structure)
 *  - "Find Best Tools" inline comparison table from Perplexity
 *  - Structure preview before committing to full generation
 *  - Sandboxed iframe preview of generated HTML
 *  - One-click download as .html file (client-side Blob)
 *  - Recent pages history grid
 */

import { useState, useEffect, useCallback } from "react";
import {
  landingPageApi,
  PAGE_GOAL_LABELS,
  type PageGoal,
  type PageStructure,
  type LandingPageRecord,
  type LandingPageTool,
} from "@/lib/api/landing-page";

interface Props {
  brandId: string;
}

const GOALS: { key: PageGoal; label: string }[] = [
  { key: "capture_email", label: "Capture Email" },
  { key: "book_call", label: "Book a Call" },
  { key: "sell_product", label: "Sell a Product" },
  { key: "build_awareness", label: "Build Awareness" },
  { key: "other", label: "Other" },
];

const SECTION_EMOJI: Record<string, string> = {
  hero: "🚀",
  problem: "😣",
  solution: "💡",
  social_proof: "⭐",
  cta: "🎯",
  faq: "❓",
};

export function LandingPageStudio({ brandId }: Props) {
  // ── Input state ──────────────────────────────────────────────────────────
  const [description, setDescription] = useState("");
  const [pageGoal, setPageGoal] = useState<PageGoal>("capture_email");
  const [targetAudience, setTargetAudience] = useState("");
  const [inspirationUrl, setInspirationUrl] = useState("");

  // ── Phase 1 — structure ──────────────────────────────────────────────────
  const [structure, setStructure] = useState<PageStructure | null>(null);
  const [structuring, setStructuring] = useState(false);
  const [structureError, setStructureError] = useState<string | null>(null);

  // ── Phase 2 — generate ───────────────────────────────────────────────────
  const [generatedHtml, setGeneratedHtml] = useState<string | null>(null);
  const [generatedTitle, setGeneratedTitle] = useState("Landing Page");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  // ── Tool research ────────────────────────────────────────────────────────
  const [tools, setTools] = useState<LandingPageTool[] | null>(null);
  const [loadingTools, setLoadingTools] = useState(false);
  const [showTools, setShowTools] = useState(false);

  // ── History ──────────────────────────────────────────────────────────────
  const [history, setHistory] = useState<LandingPageRecord[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // ── Load history ─────────────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    if (!brandId) return;
    setLoadingHistory(true);
    try {
      const data = await landingPageApi.listHistory(brandId);
      setHistory(data);
    } catch {
      // Non-critical
    } finally {
      setLoadingHistory(false);
    }
  }, [brandId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // ── Find best tools ──────────────────────────────────────────────────────
  const handleResearchTools = async () => {
    setLoadingTools(true);
    setShowTools(true);
    try {
      const result = await landingPageApi.researchTools();
      setTools(result.tools);
    } catch {
      setTools(null);
    } finally {
      setLoadingTools(false);
    }
  };

  // ── Phase 1: structure ───────────────────────────────────────────────────
  const handleStructure = async () => {
    if (description.trim().length < 5) return;
    setStructuring(true);
    setStructureError(null);
    setStructure(null);
    setGeneratedHtml(null);
    try {
      const result = await landingPageApi.structurePage({
        brand_id: brandId,
        description: description.trim(),
        page_goal: pageGoal,
        target_audience: targetAudience.trim(),
        inspiration_url: inspirationUrl.trim() || undefined,
      });
      if (result.error && !result.sections?.length) {
        setStructureError(result.error);
      } else {
        setStructure(result);
      }
    } catch (err) {
      setStructureError(err instanceof Error ? err.message : "Structure failed — please retry.");
    } finally {
      setStructuring(false);
    }
  };

  // ── Phase 2: generate ────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!structure) return;
    setGenerating(true);
    setGenError(null);
    try {
      const result = await landingPageApi.generatePage({
        brand_id: brandId,
        description: description.trim(),
        structure,
      });
      if (result.error || !result.html) {
        setGenError(result.error || "Generation failed — no HTML returned.");
      } else {
        setGeneratedHtml(result.html);
        setGeneratedTitle(result.title || "Landing Page");
        loadHistory();
      }
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Generation failed — please retry.");
    } finally {
      setGenerating(false);
    }
  };

  // ── Download HTML (client-side Blob) ─────────────────────────────────────
  const handleDownload = () => {
    if (!generatedHtml) return;
    const blob = new Blob([generatedHtml], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${generatedTitle.replace(/\s+/g, "-").toLowerCase()}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">

      {/* ── Input Panel ──────────────────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Landing Page Details</h3>
          <button
            onClick={handleResearchTools}
            disabled={loadingTools}
            className="text-xs text-primary hover:underline disabled:opacity-50"
          >
            {loadingTools ? "Searching…" : "🔍 Find Best Free Tools"}
          </button>
        </div>

        {/* Inspiration URL */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">
            Inspiration URL <span className="text-muted-foreground/50">(optional — agent will clone the structure)</span>
          </label>
          <input
            type="url"
            value={inspirationUrl}
            onChange={(e) => setInspirationUrl(e.target.value)}
            placeholder="https://example.com/landing-page"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted-foreground/50 outline-none focus:border-primary/50"
          />
        </div>

        {/* Description */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">
            What is this page for? <span className="text-red-400">*</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. A landing page for my LinkedIn ghostwriting service targeting B2B founders who want to grow their personal brand without spending hours writing..."
            rows={3}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted-foreground/50 outline-none focus:border-primary/50 resize-none"
          />
        </div>

        {/* Target audience */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Target audience</label>
          <input
            value={targetAudience}
            onChange={(e) => setTargetAudience(e.target.value)}
            placeholder="e.g. B2B SaaS founders, 30-45, scaling past $1M ARR"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted-foreground/50 outline-none focus:border-primary/50"
          />
        </div>

        {/* Page goal */}
        <div>
          <label className="text-xs text-muted-foreground mb-2 block">Page goal</label>
          <div className="flex flex-wrap gap-2">
            {GOALS.map((g) => (
              <button
                key={g.key}
                onClick={() => setPageGoal(g.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                  pageGoal === g.key
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
                }`}
              >
                {g.label}
              </button>
            ))}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleStructure}
            disabled={structuring || description.trim().length < 5}
            className="flex items-center gap-2 text-sm border border-border rounded-lg px-4 py-2 text-foreground hover:border-primary/50 transition disabled:opacity-50"
          >
            {structuring ? (
              <><span className="animate-spin">⟳</span> Blueprinting…</>
            ) : (
              <>🔍 Preview Structure</>
            )}
          </button>
          <button
            onClick={handleGenerate}
            disabled={!structure || generating}
            className="flex items-center gap-2 text-sm bg-primary text-primary-foreground rounded-lg px-4 py-2 font-medium hover:opacity-90 transition disabled:opacity-50"
          >
            {generating ? (
              <><span className="animate-spin">⟳</span> Generating…</>
            ) : (
              <>🚀 Generate Page</>
            )}
          </button>
        </div>

        {structureError && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-2.5 text-xs text-red-400">
            ⚠️ {structureError}
          </div>
        )}
      </div>

      {/* ── Tool Research Panel ───────────────────────────────────────── */}
      {showTools && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Best Free Landing Page Tools</h3>
            <button
              onClick={() => setShowTools(false)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              ✕
            </button>
          </div>

          {loadingTools ? (
            <div className="space-y-2 animate-pulse">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-10 rounded-lg bg-muted/30" />
              ))}
            </div>
          ) : tools ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="pb-2 text-left font-medium">Tool</th>
                    <th className="pb-2 text-left font-medium">Free Tier</th>
                    <th className="pb-2 text-center font-medium">Drag & Drop</th>
                    <th className="pb-2 text-center font-medium">Custom Domain</th>
                    <th className="pb-2 text-center font-medium">Templates</th>
                    <th className="pb-2 text-center font-medium">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {tools.map((tool) => (
                    <tr key={tool.name} className="hover:bg-muted/20 transition-colors">
                      <td className="py-2 font-medium text-foreground">{tool.name}</td>
                      <td className="py-2 text-muted-foreground max-w-[180px]">{tool.free_tier}</td>
                      <td className="py-2 text-center">{tool.drag_drop ? "✅" : "❌"}</td>
                      <td className="py-2 text-center">{tool.custom_domain ? "✅" : "❌"}</td>
                      <td className="py-2 text-center text-muted-foreground">{tool.templates > 0 ? tool.templates : "—"}</td>
                      <td className="py-2 text-center">
                        <span className={`font-semibold ${tool.score >= 8 ? "text-green-400" : tool.score >= 6 ? "text-amber-400" : "text-muted-foreground"}`}>
                          {tool.score}/10
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-[10px] text-muted-foreground">
                Tip: Generate the page here → download the .html file → drop it into Netlify or Carrd for instant hosting.
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Could not load tools. Check connection.</p>
          )}
        </div>
      )}

      {/* ── Structure Preview ─────────────────────────────────────────── */}
      {structure && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                Page Blueprint{structure.title ? ` — ${structure.title}` : ""}
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {structure.tone && <span className="capitalize">{structure.tone} tone</span>}
                {structure.estimated_word_count && ` · ~${structure.estimated_word_count} words`}
                {structure.color_hint && (
                  <span className="ml-2 inline-flex items-center gap-1">
                    <span
                      className="w-3 h-3 rounded-full border border-border inline-block"
                      style={{ background: structure.color_hint }}
                    />
                    {structure.color_hint}
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="space-y-2">
            {structure.sections.map((section, idx) => (
              <div key={idx} className="flex items-start gap-3 rounded-lg bg-muted/20 px-3 py-2.5">
                <span className="text-base shrink-0">{SECTION_EMOJI[section.type] ?? "📄"}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-foreground capitalize mb-0.5">
                    {section.type.replace("_", " ")}
                  </div>
                  {section.headline_direction && (
                    <p className="text-[11px] text-muted-foreground line-clamp-2">
                      {section.headline_direction}
                    </p>
                  )}
                  {section.cta_text && (
                    <span className="mt-1 inline-block text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                      CTA: {section.cta_text}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {structure.error && (
            <p className="text-[11px] text-amber-400">Note: {structure.error}</p>
          )}
        </div>
      )}

      {/* ── Generated Page ────────────────────────────────────────────── */}
      {(generating || genError || generatedHtml) && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Generated Page</h3>
            {generatedHtml && (
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium hover:opacity-90 transition"
              >
                ⬇ Download HTML
              </button>
            )}
          </div>

          {generating && (
            <div className="flex items-center gap-3 py-8 justify-center text-muted-foreground">
              <span className="animate-spin text-xl">⟳</span>
              <span className="text-sm">Claude is writing your landing page…</span>
            </div>
          )}

          {genError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-xs text-red-400">
              ⚠️ {genError}
            </div>
          )}

          {generatedHtml && !generating && (
            <iframe
              srcDoc={generatedHtml}
              sandbox="allow-scripts"
              className="w-full rounded-lg border border-border"
              style={{ height: "600px" }}
              title="Landing page preview"
            />
          )}
        </div>
      )}

      {/* ── Recent Pages ─────────────────────────────────────────────── */}
      {(history.length > 0 || loadingHistory) && (
        <div className="space-y-3">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Recent Pages
          </h3>

          {loadingHistory ? (
            <div className="grid grid-cols-2 gap-3">
              {[1, 2].map(i => (
                <div key={i} className="h-16 rounded-xl border border-border bg-muted/20 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {history.map((page) => (
                <div
                  key={page.id}
                  className="flex items-center gap-3 rounded-lg border border-border bg-card/30 px-4 py-3"
                >
                  <span className="text-base">🚀</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{page.title}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {page.page_goal ? PAGE_GOAL_LABELS[page.page_goal as keyof typeof PAGE_GOAL_LABELS] ?? page.page_goal : ""}
                      {page.model_used && ` · ${page.model_used}`}
                    </p>
                  </div>
                  <span className="text-[10px] text-muted-foreground shrink-0">
                    {new Date(page.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
