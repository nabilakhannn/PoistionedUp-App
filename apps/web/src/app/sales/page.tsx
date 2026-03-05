"use client";

/**
 * Sales Room — Slice 95 + Slice 101
 * 5 functional tabs: ICP Research / Leads / Outreach / Sequences / Newsletter
 */

import { useState } from "react";
import { useBrand } from "@/lib/brand-context";
import LeadsCRM from "@/components/leads-crm";
import NewsletterEngine from "@/components/newsletter-engine";
import OutreachQueue from "@/components/outreach-queue";
import SequencesTracker from "@/components/sequences-tracker";
import IcpResearchPanel from "@/components/icp-research-panel";

type Tab = "icp" | "leads" | "outreach" | "sequences" | "newsletter";

const TABS: { key: Tab; label: string; emoji: string }[] = [
  { key: "icp", label: "ICP Research", emoji: "🎯" },
  { key: "leads", label: "Leads", emoji: "👥" },
  { key: "outreach", label: "Outreach", emoji: "✉️" },
  { key: "sequences", label: "Sequences", emoji: "🔄" },
  { key: "newsletter", label: "Newsletter", emoji: "📧" },
];

export default function SalesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("icp");
  const { currentBrand } = useBrand();

  return (
    <div className="min-h-screen bg-background">
      {/* Page header */}
      <div className="border-b border-border bg-card/50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              💼 Sales
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              ICP research, lead nurturing, personalized outreach, and automated sequences.
            </p>
          </div>
          {currentBrand && (
            <span className="text-xs text-muted-foreground border border-border rounded-lg px-3 py-1.5">
              {currentBrand.name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 mt-4 -mb-px overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap transition ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.emoji} {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-6 py-6">
        {!currentBrand ? (
          <div className="max-w-md">
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center">
              <div className="text-2xl mb-2">💼</div>
              <p className="text-sm font-medium text-foreground mb-1">Set up a brand first</p>
              <p className="text-xs text-muted-foreground">
                Go to Settings → Brand Profile to create your brand before using the Sales room.
              </p>
            </div>
          </div>
        ) : (
          <>
            {activeTab === "icp" && (
              <div className="max-w-3xl">
                <IcpResearchPanel brandId={currentBrand.id} />
              </div>
            )}
            {activeTab === "newsletter" && (
              <NewsletterEngine brandId={currentBrand.id} />
            )}
            {activeTab === "leads" && (
              <LeadsCRM brandId={currentBrand.id} />
            )}
            {activeTab === "outreach" && (
              <OutreachQueue brandId={currentBrand.id} />
            )}
            {activeTab === "sequences" && (
              <SequencesTracker brandId={currentBrand.id} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
