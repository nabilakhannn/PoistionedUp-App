"use client";

import { useState } from "react";
import { useBrand } from "@/lib/brand-context";
import IcpResearchPanel from "@/components/icp-research-panel";
import LeadsCRM from "@/components/leads-crm";
import OutreachQueue from "@/components/outreach-queue";
import SequencesTracker from "@/components/sequences-tracker";
import NewsletterEngine from "@/components/newsletter-engine";

type Tab = "icp" | "leads" | "outreach" | "sequences" | "newsletter";

const TABS: { id: Tab; label: string }[] = [
  { id: "icp", label: "ICP Research" },
  { id: "leads", label: "Leads" },
  { id: "outreach", label: "Outreach" },
  { id: "sequences", label: "Sequences" },
  { id: "newsletter", label: "Newsletter" },
];

export default function GrowthPage() {
  const { currentBrand } = useBrand();
  const [tab, setTab] = useState<Tab>("icp");

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400">Select a brand to manage growth.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Growth</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Leads, outreach, and audience growth.</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1.5 flex-wrap">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              data-testid={`growth-tab-${t.id}`}
              className={`text-xs px-3 py-1.5 rounded-xl transition-colors ${
                tab === t.id
                  ? "bg-white/[0.06] text-zinc-200 ring-1 ring-white/[0.08]"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "icp" && <IcpResearchPanel brandId={currentBrand.id} />}
        {tab === "leads" && <LeadsCRM brandId={currentBrand.id} />}
        {tab === "outreach" && <OutreachQueue brandId={currentBrand.id} />}
        {tab === "sequences" && <SequencesTracker brandId={currentBrand.id} />}
        {tab === "newsletter" && <NewsletterEngine brandId={currentBrand.id} />}
      </div>
    </div>
  );
}
