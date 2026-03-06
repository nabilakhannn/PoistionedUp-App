"use client";

import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { MarketingCalendar } from "@/components/marketing-calendar";

export default function ContentCalendarPage() {
  const { currentBrand } = useBrand();

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-5 py-8 space-y-6">
        <div>
          <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
          <h1 className="text-xl font-bold text-zinc-100 mt-1">Calendar</h1>
          <p className="text-xs text-zinc-500 mt-0.5">See your content schedule at a glance.</p>
        </div>
        {currentBrand ? (
          <MarketingCalendar brandId={currentBrand.id} />
        ) : (
          <div className="glass-card text-center py-8">
            <p className="text-sm text-zinc-400">Select a brand to view the calendar.</p>
          </div>
        )}
      </div>
    </div>
  );
}
