"use client";

import { useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { ContentPlanChat } from "@/components/content-plan-chat";

export default function ContentTextPage() {
  const { currentBrand } = useBrand();
  const [planningOpen, setPlanningOpen] = useState(false);

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400">Select a brand first.</p>
          <Link href="/brand" className="glass-button-primary text-sm mt-3 inline-block">Go to Brand →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-4xl mx-auto px-5 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
            <h1 className="text-xl font-bold text-zinc-100 mt-1">Text Content</h1>
            <p className="text-xs text-zinc-500 mt-0.5">Create posts, threads, and ad copy with Jumbo.</p>
          </div>
          {!planningOpen && (
            <button
              onClick={() => setPlanningOpen(true)}
              className="glass-button-primary text-sm"
            >
              Plan with Jumbo
            </button>
          )}
        </div>

        {planningOpen ? (
          <ContentPlanChat
            brandId={currentBrand.id}
            onApproved={() => setPlanningOpen(false)}
            onClose={() => setPlanningOpen(false)}
          />
        ) : (
          <div className="glass-card text-center py-12">
            <p className="text-sm text-zinc-400 mb-4">
              Tell Jumbo what you want to create. He&apos;ll brainstorm topics, write drafts, and send them to your Dashboard for approval.
            </p>
            <button onClick={() => setPlanningOpen(true)} className="glass-button text-sm">
              Start Creating →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
