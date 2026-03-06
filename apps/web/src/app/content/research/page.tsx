"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { researchBriefsApi, ResearchBrief } from "@/lib/api/research-briefs";
import { CompetitorIntelEmbed } from "@/components/competitor-intel-embed";

export default function ContentResearchPage() {
  const { currentBrand } = useBrand();
  const [pillars, setPillars] = useState<string[]>([]);
  const [brief, setBrief] = useState<ResearchBrief | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentBrand?.id) return;
    setLoading(true);
    Promise.all([
      agentBridgeApi.getContext(currentBrand.id).catch(() => null),
      researchBriefsApi.getLatest(currentBrand.id).catch(() => ({ brief: null })),
    ]).then(([ctx, briefRes]) => {
      if (ctx?.content_pillars) {
        const raw: any = ctx.content_pillars;
        if (Array.isArray(raw)) setPillars(raw.map((p: any) => typeof p === "string" ? p : p.name || p.label || JSON.stringify(p)));
        else if (typeof raw === "string") setPillars(raw.split(",").map((s: string) => s.trim()).filter(Boolean));
      }
      setBrief(briefRes.brief);
    }).finally(() => setLoading(false));
  }, [currentBrand?.id]);

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400">Select a brand to view content research.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-4xl mx-auto px-5 py-8 space-y-6">
        <div>
          <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
          <h1 className="text-xl font-bold text-zinc-100 mt-1">Content Research</h1>
          <p className="text-xs text-zinc-500 mt-0.5">What to post now — trends, gaps, and pillars.</p>
        </div>

        {loading ? (
          <div className="glass-card py-8 text-center text-xs text-zinc-500">Loading...</div>
        ) : (
          <>
            {/* Content Pillars */}
            <section className="glass-card">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">Content Pillars</h2>
              {pillars.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {pillars.map((p, i) => (
                    <span key={i} className="glass-badge-accent">{p}</span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-zinc-600">No pillars yet. Run brand research first.</p>
              )}
            </section>

            {/* Latest Research Brief */}
            {brief && (
              <section className="glass-card">
                <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">Latest Research Brief</h2>
                <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{brief.content}</p>
              </section>
            )}

            {/* Competitor Intel */}
            <section>
              <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">Competitor Landscape</h2>
              <CompetitorIntelEmbed brandId={currentBrand.id} />
            </section>
          </>
        )}
      </div>
    </div>
  );
}
