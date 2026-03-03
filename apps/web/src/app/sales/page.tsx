"use client";

/**
 * Sales Room — Slice 90
 * 4 tabs: Newsletter / Leads / Outreach / Sequences
 */

import { useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";

type Tab = "newsletter" | "leads" | "outreach" | "sequences";

const TABS: { key: Tab; label: string; emoji: string }[] = [
  { key: "newsletter", label: "Newsletter", emoji: "📧" },
  { key: "leads", label: "Leads", emoji: "👥" },
  { key: "outreach", label: "Outreach", emoji: "✉️" },
  { key: "sequences", label: "Sequences", emoji: "🔄" },
];

const LEAD_COLUMNS = [
  { key: "cold", label: "Cold", emoji: "❄️", color: "text-blue-400" },
  { key: "warm", label: "Warm", emoji: "🔥", color: "text-amber-400" },
  { key: "hot", label: "Hot", emoji: "⚡", color: "text-orange-400" },
  { key: "customer", label: "Customer", emoji: "✅", color: "text-green-400" },
];

export default function SalesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("newsletter");
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
              Newsletter, lead nurturing, personalized outreach, and automated sequences.
            </p>
          </div>
          {currentBrand && (
            <span className="text-xs text-muted-foreground border border-border rounded-lg px-3 py-1.5">
              {currentBrand.name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 mt-4 -mb-px">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
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
        {/* ── NEWSLETTER TAB ─────────────────────────── */}
        {activeTab === "newsletter" && (
          <div className="space-y-4 max-w-2xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Weekly Newsletter</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Jumbo writes a 400-600 word weekly email based on what performed best in Marketing this week.
                You approve → Resend SMTP sends it.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
              <div className="rounded-lg bg-muted/30 border border-border p-4">
                <div className="text-xs text-muted-foreground mb-1">Sales agents automatically read what Marketing researched via research_briefs table.</div>
                <div className="text-xs font-medium text-foreground">Latest research brief will inform your next newsletter.</div>
              </div>

              <div className="opacity-60">
                <div className="text-sm font-semibold text-foreground mb-1">Newsletter Engine</div>
                <div className="text-xs text-muted-foreground">
                  Auto-generated weekly newsletters with open rate tracking coming in Slice 91.
                </div>
                <span className="inline-block mt-2 text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full">Slice 91</span>
              </div>
            </div>
          </div>
        )}

        {/* ── LEADS TAB ──────────────────────────────── */}
        {activeTab === "leads" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Lead CRM</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Cold → Warm → Hot → Customer. Agents find and move leads automatically.</p>
              </div>
              <span className="text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full">Slice 91</span>
            </div>

            <div className="grid grid-cols-4 gap-3">
              {LEAD_COLUMNS.map((col) => (
                <div key={col.key} className="rounded-xl border border-border bg-card/40 p-3">
                  <div className={`text-xs font-semibold mb-2 ${col.color}`}>
                    {col.emoji} {col.label}
                  </div>
                  <div className="min-h-[120px] flex items-center justify-center">
                    <p className="text-[10px] text-muted-foreground/40 text-center">
                      Lead Finder agent will auto-populate in Slice 91
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── OUTREACH TAB ───────────────────────────── */}
        {activeTab === "outreach" && (
          <div className="space-y-4 max-w-2xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Personalized Outreach</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                LinkedIn messages and cold emails written in YOUR voice, personalized per lead.
                Draws from what's working in Marketing this week.
              </p>
            </div>

            <div className="grid gap-3">
              {[
                { icon: "💼", title: "LinkedIn Messages", desc: "Personalized per lead, in your voice + ICA. Connect → value → offer.", badge: "Slice 91" },
                { icon: "📧", title: "Cold Email", desc: "Sent via Resend (30/hr limit). Unsubscribe auto-appended. Open tracking.", badge: "Slice 91" },
              ].map((item) => (
                <div key={item.title} className="rounded-xl border border-border/50 bg-card/30 p-4 opacity-60">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center text-base">{item.icon}</div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">{item.title}</div>
                    </div>
                    <span className="ml-auto text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full">{item.badge}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── SEQUENCES TAB ──────────────────────────── */}
        {activeTab === "sequences" && (
          <div className="space-y-4 max-w-2xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Outreach Sequences</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                3-message cadence: connect → value → offer (2-week timeline). Written in your voice, personalized per lead.
              </p>
            </div>

            <div className="rounded-xl border border-border/50 bg-card/30 px-6 py-12 text-center opacity-60">
              <div className="text-3xl mb-3">🔄</div>
              <p className="text-sm font-medium text-foreground mb-1">Automated Sequences</p>
              <p className="text-xs text-muted-foreground">3-step automated outreach cadence with personalization coming in Slice 92.</p>
              <span className="inline-block mt-3 text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full">Slice 92</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
