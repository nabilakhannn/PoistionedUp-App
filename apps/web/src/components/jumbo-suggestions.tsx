"use client";

/**
 * Jumbo Suggestions — Slice 102 (Fix G)
 * Floating proactive suggestion bubble (bottom right, every page).
 * Polls /agent-api/suggestions every 5 min.
 */

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { useBrand } from "@/lib/brand-context";

// Needed for useSuggestions to work on first load without flash
let _cachedSuggestions: Suggestion[] = [];

interface Suggestion {
  id: string;
  priority: "urgent" | "high" | "normal";
  trigger_type: string;
  title: string;
  body: string;
  action_url: string;
  cta: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "border-red-500/40 bg-red-500/5",
  high:   "border-amber-500/40 bg-amber-500/5",
  normal: "border-border bg-card/80",
};

const PRIORITY_DOT: Record<string, string> = {
  urgent: "bg-red-400 animate-pulse",
  high:   "bg-amber-400",
  normal: "bg-blue-400",
};

export function JumboSuggestions() {
  const { currentBrand } = useBrand();
  const [suggestions, setSuggestions] = useState<Suggestion[]>(_cachedSuggestions);
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const load = useCallback(() => {
    agentBridgeApi.getProactiveSuggestions(currentBrand?.id)
      .then((data) => {
        if (data?.suggestions) {
          _cachedSuggestions = data.suggestions;
          setSuggestions(data.suggestions);
        }
      })
      .catch(() => {});
  }, [currentBrand?.id]);

  useEffect(() => {
    // Delay first load by 3s so it doesn't block initial render
    const initial = setTimeout(load, 3000);
    const interval = setInterval(load, 5 * 60 * 1000); // every 5 min
    return () => { clearTimeout(initial); clearInterval(interval); };
  }, [load]);

  const visible = suggestions.filter((s) => !dismissed.has(s.id));
  const urgentCount = visible.filter((s) => s.priority === "urgent" || s.priority === "high").length;
  const topSuggestion = visible[0];

  if (visible.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {/* Expanded list */}
      {open && (
        <div className="w-80 max-h-[70vh] overflow-y-auto bg-[#0d1117] border border-border rounded-2xl shadow-2xl flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <span className="text-base">🧠</span>
              <span className="text-sm font-semibold text-foreground">Jumbo Suggestions</span>
              <span className="text-[10px] text-muted-foreground">{visible.length} active</span>
            </div>
            <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground transition">
              ✕
            </button>
          </div>
          <div className="divide-y divide-border/50 overflow-y-auto">
            {visible.map((s) => (
              <div key={s.id} className={`p-4 space-y-2 border-l-2 ${s.priority === "urgent" ? "border-l-red-400" : s.priority === "high" ? "border-l-amber-400" : "border-l-blue-400"}`}>
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-semibold text-foreground leading-tight">{s.title}</p>
                  <button
                    onClick={() => setDismissed((prev) => new Set([...prev, s.id]))}
                    className="shrink-0 text-muted-foreground/50 hover:text-muted-foreground transition text-[10px]"
                  >
                    ✕
                  </button>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">{s.body}</p>
                <Link
                  href={s.action_url}
                  onClick={() => setOpen(false)}
                  className="inline-block text-[10px] px-2.5 py-1 rounded-lg bg-primary/15 text-primary border border-primary/20 hover:bg-primary/25 transition font-medium"
                >
                  {s.cta} →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collapsed bubble */}
      {!open && topSuggestion && (
        <button
          onClick={() => setOpen(true)}
          className={`flex items-start gap-3 p-3 rounded-2xl shadow-xl border backdrop-blur-sm max-w-[280px] text-left transition hover:scale-[1.02] ${PRIORITY_COLORS[topSuggestion.priority]}`}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-sm">🧠</span>
              <span className="text-[10px] font-semibold text-foreground">Jumbo</span>
              {urgentCount > 0 && (
                <span className={`w-2 h-2 rounded-full shrink-0 ${PRIORITY_DOT[topSuggestion.priority]}`} />
              )}
            </div>
            <p className="text-xs text-foreground/90 leading-tight line-clamp-2">{topSuggestion.title}</p>
          </div>
          {visible.length > 1 && (
            <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-mono">
              +{visible.length - 1}
            </span>
          )}
        </button>
      )}
    </div>
  );
}
