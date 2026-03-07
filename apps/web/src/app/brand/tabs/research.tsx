"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import BrandIntelligenceReport from "@/components/brand-intelligence-report";
import { clientResearchApi, type ClientDossier } from "@/lib/api/client-research";

const RESEARCH_MODES = [
  {
    id: "ai",
    icon: "🤖",
    title: "AI Research",
    subtitle: "Do it for me",
    desc: "Provide your name, LinkedIn URL, and website. AI does the rest in ~30 seconds.",
    cta: "Start",
    href: (brandId: string) => `/brands/${brandId}?mode=ai`,
  },
  {
    id: "guided",
    icon: "🧭",
    title: "Guided Research",
    subtitle: "Interview me",
    desc: "Jumbo asks you questions and fills your profile from your answers. Conversational and thorough.",
    cta: "Begin Chat",
    href: (brandId: string) => `/brands/${brandId}/strategist`,
  },
  {
    id: "manual",
    icon: "✍️",
    title: "Deep Dive",
    subtitle: "I'll fill it in",
    desc: "Full 8-section forms. You see every field. Most thorough option.",
    cta: "Open Forms",
    href: (brandId: string) => `/brands/${brandId}`,
  },
  {
    id: "icp",
    icon: "🎯",
    title: "ICP Research",
    subtitle: "Know your dream client",
    desc: "4-stage AI pipeline: define your ideal customer, find where they are, and build Apollo.io filter sets.",
    cta: "Research ICP",
    href: (_brandId: string) => `/growth?tab=icp`,
  },
];

export function BrandResearchTab({ brandId }: { brandId: string }) {
  const [dossier, setDossier] = useState<ClientDossier | null>(null);
  const [brandName, setBrandName] = useState("Brand");
  const [loadingDossier, setLoadingDossier] = useState(true);

  useEffect(() => {
    (async () => {
      setLoadingDossier(true);
      try {
        const report = await clientResearchApi.getReport(brandId).catch(() => null);
        if (report?.profile) setDossier(report.profile as ClientDossier);
        if (report?.name) setBrandName(report.name);
      } finally {
        setLoadingDossier(false);
      }
    })();
  }, [brandId]);

  return (
    <div className="space-y-8">
      {/* Mode cards */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-200 mb-1">Research Your Brand</h2>
        <p className="text-xs text-zinc-500 mb-4">
          Choose how to build your brand profile. All modes produce the same 8-section dossier.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {RESEARCH_MODES.map((mode) => (
            <div key={mode.id} className="glass-card flex flex-col justify-between">
              <div>
                <span className="text-2xl">{mode.icon}</span>
                <h3 className="text-sm font-semibold text-zinc-200 mt-3">{mode.title}</h3>
                <p className="text-xs text-violet-400/80 font-medium">{mode.subtitle}</p>
                <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{mode.desc}</p>
              </div>
              <Link href={mode.href(brandId)} className="glass-button-primary text-sm mt-4 text-center">
                {mode.cta} →
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* Dossier output */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Brand Intelligence Report
          </h2>
          <div className="flex-1 h-px bg-white/[0.04]" />
        </div>

        {loadingDossier ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-32 rounded-2xl bg-white/[0.03] animate-pulse" />
            ))}
          </div>
        ) : dossier ? (
          <BrandIntelligenceReport brandId={brandId} dossier={dossier} clientName={brandName} />
        ) : (
          <div className="glass-card text-center py-8">
            <p className="text-sm text-zinc-400 mb-1">No research dossier yet.</p>
            <p className="text-xs text-zinc-500">
              Run AI Research, Guided Research, or Deep Dive above to generate your intelligence report.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
