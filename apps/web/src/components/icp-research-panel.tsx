"use client";

/**
 * IcpResearchPanel — Sales Lead Research System Prompt Methodology
 *
 * 4-stage visible pipeline based on the Sales Lead Research template:
 *   Stage 1: Objective           — derived from brand profile
 *   Stage 2: Brand Snapshot      — founder, product, mission, pricing
 *   Stage 3: Research Questions  — Perplexity searches for ICP signals
 *   Stage 4: Apollo Filters      — company + contact + keyword output
 *
 * Users can see exactly which stage the agent is working on.
 */

import { useState, useCallback } from "react";
import { leadsApi } from "@/lib/api/leads";

interface Props {
  brandId: string;
}

interface IcpStage {
  id: number;
  name: string;
  status: "pending" | "running" | "complete" | "error";
  result?: Record<string, unknown>;
}

const STAGE_DESCRIPTIONS: Record<number, string> = {
  1: "Define what you are trying to achieve — product, pricing, and lead sourcing goal.",
  2: "Build the brand & product snapshot from your profile — founder, mission, deliverables.",
  3: "AI researches ideal companies, decision-makers, industries, and pain points using Perplexity.",
  4: "Generate Apollo.io company filters, contact filters, and keyword/tech criteria.",
};

const STAGE_ICONS: Record<number, string> = {
  1: "🎯",
  2: "🏢",
  3: "🔍",
  4: "⚙️",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="text-[10px] text-slate-500 hover:text-indigo-400 transition"
    >
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

function FilterList({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span key={i} className="px-2 py-0.5 bg-indigo-950/50 border border-indigo-500/20 text-indigo-300 text-[11px] rounded-full">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function StageCard({ stage, isActive }: { stage: IcpStage; isActive: boolean }) {
  const [open, setOpen] = useState(false);
  const r = stage.result || {};

  const statusBadge = {
    pending: <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500">Pending</span>,
    running: (
      <span className="flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-full bg-indigo-950/50 text-indigo-400 border border-indigo-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
        Running...
      </span>
    ),
    complete: <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-950/50 text-green-400 border border-green-500/30">✓ Complete</span>,
    error: <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-950/50 text-red-400 border border-red-500/30">Error</span>,
  }[stage.status];

  return (
    <div className={`rounded-xl border transition-colors ${isActive && stage.status === "running" ? "border-indigo-500/40 bg-indigo-950/10" : stage.status === "complete" ? "border-green-500/20 bg-green-950/5" : "border-white/10 bg-white/[0.02]"}`}>
      <button
        className="w-full flex items-center gap-3 p-4 text-left"
        onClick={() => stage.status === "complete" && setOpen((o) => !o)}
      >
        <span className="text-xl shrink-0">{STAGE_ICONS[stage.id]}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-white">Stage {stage.id}: {stage.name}</span>
            {statusBadge}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">{STAGE_DESCRIPTIONS[stage.id]}</p>
        </div>
        {stage.status === "complete" && (
          <span className="text-slate-600 text-xs shrink-0">{open ? "▲" : "▼"}</span>
        )}
      </button>

      {open && stage.status === "complete" && (
        <div className="px-4 pb-4 space-y-4 border-t border-white/5 pt-4">
          {stage.id === 1 && (
            <div className="space-y-2 text-sm">
              <p><span className="text-slate-500">Product:</span> <span className="text-white">{String(r.product_service_name || "")}</span></p>
              <p><span className="text-slate-500">Pricing:</span> <span className="text-white">{String(r.pricing || "")}</span></p>
              <p><span className="text-slate-500">Goal:</span> <span className="text-white">{String(r.goal || "")}</span></p>
              <p><span className="text-slate-500">Lead DB:</span> <span className="text-white">{String(r.lead_database || "Apollo.io")} → {String(r.scraping_tool || "Apify")}</span></p>
            </div>
          )}

          {stage.id === 2 && (
            <div className="space-y-2 text-sm">
              {!!r.founder && <p><span className="text-slate-500">Founder:</span> <span className="text-white">{String(r.founder)}</span></p>}
              {!!r.positioning && <p><span className="text-slate-500">Positioning:</span> <span className="text-white">{String(r.positioning)}</span></p>}
              {!!r.mission && <p><span className="text-slate-500">Mission:</span> <span className="text-white">{String(r.mission)}</span></p>}
              {!!r.philosophy && <p><span className="text-slate-500">Tagline:</span> <span className="text-white italic">&ldquo;{String(r.philosophy)}&rdquo;</span></p>}
              {!!r.ideal_outcome && <p><span className="text-slate-500">Outcome:</span> <span className="text-white">{String(r.ideal_outcome)}</span></p>}
              {Array.isArray(r.key_features) && r.key_features.length > 0 && (
                <div>
                  <p className="text-slate-500 text-[11px] mb-1">Key Features:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {r.key_features.map((f, i) => <li key={i} className="text-white text-[11px]">{String(f)}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          {stage.id === 3 && (
            <div className="space-y-3">
              <FilterList label="Target Industries" items={(r.ideal_industries as string[]) || []} />
              <FilterList label="Company Sizes" items={(r.company_size_ranges as string[]) || []} />
              <FilterList label="Target Regions" items={(r.target_regions as string[]) || []} />
              <FilterList label="Job Titles" items={(r.job_titles as string[]) || []} />
              <FilterList label="Seniority Levels" items={(r.seniority_levels as string[]) || []} />
              {Array.isArray(r.pain_points) && r.pain_points.length > 0 && (
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1.5">Pain Points</p>
                  <ul className="space-y-1">
                    {(r.pain_points as string[]).map((p, i) => (
                      <li key={i} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                        <span className="text-red-400 shrink-0 mt-0.5">•</span>{p}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {Array.isArray(r.motivations) && r.motivations.length > 0 && (
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1.5">Motivations</p>
                  <ul className="space-y-1">
                    {(r.motivations as string[]).map((m, i) => (
                      <li key={i} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                        <span className="text-green-400 shrink-0 mt-0.5">•</span>{m}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {stage.id === 4 && (
            <div className="space-y-4">
              {/* Company Filters */}
              {!!r.company_filters && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-slate-300">Company Filters (Apollo.io)</p>
                  <FilterList label="Industry" items={((r.company_filters as Record<string, string[]>).industry) || []} />
                  <FilterList label="Company Size" items={((r.company_filters as Record<string, string[]>).size) || []} />
                  <FilterList label="Revenue" items={((r.company_filters as Record<string, string[]>).revenue) || []} />
                  <FilterList label="Location" items={((r.company_filters as Record<string, string[]>).location) || []} />
                </div>
              )}

              {/* Contact Filters */}
              {!!r.contact_filters && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-slate-300">Contact Filters (Apollo.io)</p>
                  <FilterList label="Job Titles" items={((r.contact_filters as Record<string, string[]>).job_titles) || []} />
                  <FilterList label="Seniority" items={((r.contact_filters as Record<string, string[]>).seniority) || []} />
                </div>
              )}

              {/* Keywords */}
              {Array.isArray(r.keywords_tech) && <FilterList label="Keywords / Tech" items={(r.keywords_tech as string[])} />}

              {/* Apollo hint */}
              {!!r.apollo_search_hint && (
                <div className="bg-indigo-950/30 border border-indigo-500/20 rounded-xl p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-[10px] text-indigo-400 uppercase tracking-wide mb-1.5">Apollo.io Search Hint</p>
                      <p className="text-[11px] text-slate-300">{String(r.apollo_search_hint)}</p>
                    </div>
                    <CopyButton text={String(r.apollo_search_hint)} />
                  </div>
                </div>
              )}

              {/* Apify hint */}
              {!!r.apify_scraper && (
                <div className="bg-amber-950/20 border border-amber-500/20 rounded-xl p-3">
                  <p className="text-[10px] text-amber-400 uppercase tracking-wide mb-1">Next Step</p>
                  <p className="text-[11px] text-slate-300">{String(r.apify_scraper)}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function IcpResearchPanel({ brandId }: Props) {
  const [stages, setStages] = useState<IcpStage[]>([
    { id: 1, name: "Objective", status: "pending" },
    { id: 2, name: "Brand & Product Snapshot", status: "pending" },
    { id: 3, name: "Research Questions", status: "pending" },
    { id: 4, name: "Output / Apollo Filters", status: "pending" },
  ]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [productOverride, setProductOverride] = useState("");
  const [pricingOverride, setPricingOverride] = useState("");
  const [activeStage, setActiveStage] = useState<number | null>(null);

  const runResearch = useCallback(async () => {
    setRunning(true);
    setError(null);

    // Reset all to pending
    setStages([
      { id: 1, name: "Objective", status: "pending" },
      { id: 2, name: "Brand & Product Snapshot", status: "pending" },
      { id: 3, name: "Research Questions", status: "pending" },
      { id: 4, name: "Output / Apollo Filters", status: "pending" },
    ]);

    // Show stages 1 & 2 running immediately (they use brand profile, fast)
    setActiveStage(1);
    setStages((prev) => prev.map((s) => s.id <= 2 ? { ...s, status: "running" } : s));

    try {
      const result = await leadsApi.icpResearch(brandId, {
        product_name: productOverride || undefined,
        pricing: pricingOverride || undefined,
      });

      // Animate stage completion as data arrives
      for (const stage of result.stages) {
        const safeStatus = stage.status as IcpStage["status"];
        setActiveStage(stage.id);
        setStages((prev) => prev.map((s) =>
          s.id === stage.id ? { ...s, status: safeStatus, result: stage.result } :
          s.id === stage.id + 1 && stage.id < 4 ? { ...s, status: "running" as const } : s
        ));
        if (stage.id < result.stages.length) {
          await new Promise((r) => setTimeout(r, 400));
        }
      }
      setActiveStage(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "ICP research failed — check your brand profile is complete");
      setStages((prev) => prev.map((s) => s.status === "running" ? { ...s, status: "error" } : s));
    } finally {
      setRunning(false);
    }
  }, [brandId, productOverride, pricingOverride]);

  const allDone = stages.every((s) => s.status === "complete");

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-950/40 to-purple-950/30 border border-indigo-500/20 rounded-2xl p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold text-white mb-1">Sales Lead Research System</h3>
            <p className="text-[12px] text-slate-400 max-w-lg">
              4-stage ICP research methodology — AI researches your ideal customer profile, then outputs ready-to-use Apollo.io filters for lead scraping.
            </p>
          </div>
          {allDone && (
            <span className="shrink-0 text-[10px] px-2.5 py-1 rounded-full bg-green-900/50 border border-green-500/30 text-green-400 font-medium">
              ✓ Research Complete
            </span>
          )}
        </div>

        {/* Optional overrides */}
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div>
            <label className="text-[10px] text-slate-500 uppercase tracking-wide block mb-1">Product name override</label>
            <input
              value={productOverride}
              onChange={(e) => setProductOverride(e.target.value)}
              placeholder="Auto from brand profile"
              disabled={running}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/60 disabled:opacity-40"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-500 uppercase tracking-wide block mb-1">Pricing override</label>
            <input
              value={pricingOverride}
              onChange={(e) => setPricingOverride(e.target.value)}
              placeholder="e.g. $97/mo, $2,500/project"
              disabled={running}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/60 disabled:opacity-40"
            />
          </div>
        </div>

        <button
          onClick={runResearch}
          disabled={running}
          className="mt-4 w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition"
        >
          {running ? "Running ICP Research..." : allDone ? "🔄 Re-run Research" : "🔍 Run ICP Research"}
        </button>
      </div>

      {error && (
        <div className="px-4 py-3 bg-red-950/30 border border-red-500/30 text-red-400 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Stage pipeline */}
      <div className="space-y-2">
        <p className="text-[10px] text-slate-500 uppercase tracking-wider px-1">Research Pipeline</p>
        {stages.map((stage) => (
          <StageCard key={stage.id} stage={stage} isActive={activeStage === stage.id} />
        ))}
      </div>

      {/* Methodology reference */}
      <details className="group">
        <summary className="text-[11px] text-slate-600 hover:text-slate-400 cursor-pointer list-none flex items-center gap-1.5 transition">
          <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
          View ICP Methodology Template
        </summary>
        <div className="mt-3 bg-white/[0.02] border border-white/10 rounded-xl p-4 space-y-4">
          {[
            { num: 1, title: "Objective", desc: "Research and identify the best-fit target audience (ICP) and decision-makers for your product. Goal: Define exact parameters for lead generation and outreach. Tools: Apollo.io + Apify scraper." },
            { num: 2, title: "Brand & Product Snapshot", desc: "Founder name + positioning, mission, philosophy, product details, pricing, goal (e.g. 100 paying users), platform, deliverables (what customers get)." },
            { num: 3, title: "Research Questions", desc: "1. Who are the ideal companies and decision-makers? 2. What industries, company sizes, regions, and job titles benefit most? 3. What are their main pain points? 4. What data points needed for outreach? 5. Apollo.io compatibility?" },
            { num: 4, title: "Output / Report Structure", desc: "Company Filters: Industry, Size, Revenue, Location. Contact Filters: Job Titles, Seniority. Keywords/Tech. → Final Input for Apify: unique Apollo.io URL after applying all filters." },
          ].map((s) => (
            <div key={s.num} className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-indigo-950/50 border border-indigo-500/30 text-indigo-400 text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5">{s.num}</span>
              <div>
                <p className="text-[12px] font-semibold text-slate-300">{s.title}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
