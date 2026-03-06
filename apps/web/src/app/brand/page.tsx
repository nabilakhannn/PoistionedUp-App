"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { BrandResearchTab } from "./tabs/research";
import { BrandProfileTab } from "./tabs/profile";
import { BrandTeamTab } from "./tabs/team";
import { BrandSettingsTab } from "./tabs/settings/index";

type Tab = "research" | "profile" | "team" | "settings";

const TABS: { id: Tab; label: string }[] = [
  { id: "research", label: "Research" },
  { id: "profile", label: "Profile" },
  { id: "team", label: "Team" },
  { id: "settings", label: "Settings" },
];

export default function BrandPage() {
  const { currentBrand } = useBrand();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("profile");

  useEffect(() => {
    const t = searchParams.get("tab") as Tab | null;
    if (t && TABS.some((x) => x.id === t)) setTab(t);
  }, [searchParams]);

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">No brand selected. Create one to get started.</p>
          <Link href="/brands/new" className="glass-button-primary text-sm">Create Brand →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-zinc-100">{currentBrand.name}</h1>
            {currentBrand.description && (
              <p className="text-xs text-zinc-500 mt-0.5">{currentBrand.description}</p>
            )}
          </div>
          <Link href={`/brands/${currentBrand.id}`} className="glass-button text-xs">
            Edit Profile
          </Link>
        </div>

        {/* Tabs */}
        <div className="flex gap-1.5">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              data-testid={`brand-tab-${t.id}`}
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

        {/* Tab content */}
        {tab === "research" && <BrandResearchTab brandId={currentBrand.id} />}
        {tab === "profile" && <BrandProfileTab brandId={currentBrand.id} />}
        {tab === "team" && <BrandTeamTab brandId={currentBrand.id} />}
        {tab === "settings" && <BrandSettingsTab brandId={currentBrand.id} />}
      </div>
    </div>
  );
}
