"use client";

import { useEffect, useState } from "react";
import { notificationsApi, AgentNotification } from "@/lib/api/notifications";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function DailyBriefingCard() {
  const [briefing, setBriefing] = useState<AgentNotification | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    notificationsApi.latestBriefing().then((data) => {
      if (data) {
        // Only show today's briefing
        const today = new Date().toISOString().slice(0, 10);
        const briefingDate = data.created_at.slice(0, 10);
        if (briefingDate === today) {
          setBriefing(data);
        }
      }
    }).catch(() => {});
  }, []);

  if (!briefing) return null;

  return (
    <div className="mx-5 mb-4 rounded-xl border border-amber-500/20 bg-gradient-to-r from-amber-500/5 to-zinc-900">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-3 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">📋</span>
          <div>
            <h3 className="text-sm font-semibold text-amber-300">{briefing.title}</h3>
            <p className="text-[10px] text-zinc-500">
              From Jumbo &middot; {timeAgo(briefing.created_at)}
            </p>
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-zinc-500 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {expanded && (
        <div className="px-5 pb-4 border-t border-zinc-800/50">
          <div className="mt-3 text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">
            {briefing.body}
          </div>
        </div>
      )}
    </div>
  );
}
