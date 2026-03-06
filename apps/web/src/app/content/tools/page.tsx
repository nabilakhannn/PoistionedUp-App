"use client";

import { useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { ImageStudio } from "@/components/image-studio";
import { LandingPageStudio } from "@/components/landing-page-studio";

type ToolTab = "ads" | "images" | "landing";

export default function ContentToolsPage() {
  const { currentBrand } = useBrand();
  const [tab, setTab] = useState<ToolTab>("images");

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400">Select a brand first.</p>
        </div>
      </div>
    );
  }

  const TABS: { id: ToolTab; label: string }[] = [
    { id: "images", label: "Images" },
    { id: "landing", label: "Landing Pages" },
    { id: "ads", label: "Ad Creative" },
  ];

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
        <div>
          <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
          <h1 className="text-xl font-bold text-zinc-100 mt-1">Tools</h1>
        </div>

        <div className="flex gap-1.5">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
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

        {tab === "images" && <ImageStudio brandId={currentBrand.id} />}
        {tab === "landing" && <LandingPageStudio brandId={currentBrand.id} />}
        {tab === "ads" && (
          <div className="glass-card text-center py-8">
            <p className="text-sm text-zinc-400">
              Generate 40 ad variations (5 hooks × 8 angles).
            </p>
            <Link href="/ad-creative" className="glass-button-primary text-sm mt-3 inline-block">
              Open Ad Creative Studio →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
