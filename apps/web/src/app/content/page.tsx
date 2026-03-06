"use client";

import Link from "next/link";
import { useBrand } from "@/lib/brand-context";

const CONTENT_CARDS = [
  { href: "/content/text", icon: "pencil-square", label: "Text", desc: "Posts, ads, threads" },
  { href: "/content/video", icon: "film", label: "Video", desc: "Scripts & generation" },
  { href: "/content/library", icon: "archive-box", label: "Library", desc: "All content" },
  { href: "/content/pipeline", icon: "arrows-right-left", label: "Pipeline", desc: "Kanban board" },
  { href: "/content/calendar", icon: "calendar-days", label: "Calendar", desc: "Schedule" },
  { href: "/content/results", icon: "chart-bar", label: "Results", desc: "Analytics" },
  { href: "/content/research", icon: "magnifying-glass", label: "Research", desc: "Content research" },
  { href: "/content/hooks", icon: "bolt", label: "Hooks", desc: "Hook library" },
  { href: "/content/tools", icon: "wrench", label: "Tools", desc: "Ads, images, LP" },
  { href: "/content/stories", icon: "book-open", label: "Story Bank", desc: "Your material" },
  { href: "/content/agents", icon: "cpu-chip", label: "AI Agents", desc: "Workflow marketplace" },
] as const;

/* Minimal heroicons-outline paths (24x24) */
const ICON_PATHS: Record<string, string> = {
  "pencil-square": "m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10",
  film: "M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-2.625 0V5.625m0 0A1.125 1.125 0 0 1 4.5 4.5h15a1.125 1.125 0 0 1 1.125 1.125m-17.25 0v1.5c0 .621.504 1.125 1.125 1.125M20.625 5.625v12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-1.5A1.125 1.125 0 0 1 18 18.375M20.625 4.5H19.5m0 0h-1.5m1.5 0v1.5",
  "archive-box": "m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z",
  "arrows-right-left": "M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
  "calendar-days": "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6h.008v.008H12v-.008ZM12 15h.008v.008H12V15Zm0 2.25h.008v.008H12v-.008ZM9.75 15h.008v.008H9.75V15Zm0 2.25h.008v.008H9.75v-.008ZM7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm6.75-4.5h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V15Zm0 2.25h.008v.008h-.008v-.008Zm2.25-4.5h.008v.008H16.5v-.008Zm0 2.25h.008v.008H16.5V15Z",
  "chart-bar": "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z",
  "magnifying-glass": "m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z",
  bolt: "m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z",
  wrench: "M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085",
  "book-open": "M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25",
  "cpu-chip": "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 0 0 2.25-2.25V6.75a2.25 2.25 0 0 0-2.25-2.25H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5a2.25 2.25 0 0 0 2.25 2.25Zm.75-12h9v9h-9v-9Z",
};

export default function ContentPage() {
  const { currentBrand } = useBrand();

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">Select a brand to see your content workspace.</p>
          <Link href="/brand" className="glass-button-primary text-sm">Go to Brand →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">

        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Content</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Create, plan, and manage all your content.</p>
        </div>

        {/* Card grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {CONTENT_CARDS.map((card) => (
            <Link
              key={card.href}
              href={card.href}
              data-testid={`content-card-${card.label.toLowerCase()}`}
              className="glass-card-hover group flex flex-col gap-3 p-5"
            >
              <svg className="w-6 h-6 text-zinc-500 group-hover:text-violet-400 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d={ICON_PATHS[card.icon]} />
              </svg>
              <div>
                <h3 className="text-sm font-semibold text-zinc-200 group-hover:text-zinc-100">{card.label}</h3>
                <p className="text-xs text-zinc-600 mt-0.5">{card.desc}</p>
              </div>
            </Link>
          ))}
        </div>

      </div>
    </div>
  );
}
