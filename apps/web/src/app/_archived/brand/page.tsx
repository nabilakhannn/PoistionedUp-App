"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { brandApi, BrandCompleteness } from "../../lib/api";

interface Stage {
  number: number;
  key: string;
  title: string;
  question: string;
  description: string;
  chatPath: string | null;
  editPath: string | null;
  percentKey: keyof BrandCompleteness | null;
  ready: boolean;
}

const stages: Stage[] = [
  {
    number: 1,
    key: "foundation",
    title: "Foundation",
    question: "Who are you?",
    description:
      "Your beliefs, IT factor, achievements, stories, and content pillars. This is where your brand starts.",
    chatPath: "/brand/chat/foundation",
    editPath: "/brand/foundation",
    percentKey: "foundation_percent",
    ready: true,
  },
  {
    number: 2,
    key: "ica",
    title: "Ideal Client Avatar",
    question: "Who do you serve?",
    description:
      "Define your dream client: demographics, motivations, pains, desires, and fears.",
    chatPath: "/brand/chat/ica",
    editPath: "/brand/ica",
    percentKey: "ica_percent",
    ready: true,
  },
  {
    number: 3,
    key: "offer",
    title: "Your Offer",
    question: "What do you sell?",
    description:
      "Craft your offer: outcome, timeline, pricing, framework, and objections.",
    chatPath: "/brand/chat/offer",
    editPath: "/brand/offer",
    percentKey: "offer_percent",
    ready: true,
  },
  {
    number: 4,
    key: "brand",
    title: "Brand Statement",
    question: "How do you position yourself?",
    description:
      "Your positioning statement, unfair advantage leverage, and content pillars.",
    chatPath: "/brand/chat/brand",
    editPath: "/brand/strategy",
    percentKey: "brand_percent",
    ready: true,
  },
  {
    number: 5,
    key: "authority",
    title: "Authority Building",
    question: "How do you build trust?",
    description:
      "Your credentials, certifications, case studies, testimonials, media features, and social proof.",
    chatPath: "/brand/chat/authority",
    editPath: null,
    percentKey: "authority_percent",
    ready: true,
  },
  {
    number: 6,
    key: "messaging",
    title: "Messaging",
    question: "What do you say and how?",
    description:
      "Key phrases, talking points, content themes, brand voice, and signature expressions.",
    chatPath: "/brand/chat/messaging",
    editPath: null,
    percentKey: "messaging_percent",
    ready: true,
  },
  {
    number: 7,
    key: "positioning",
    title: "Positioning",
    question: "Where do you stand in the market?",
    description:
      "Market position, competitive angle, category design, and your unique wedge.",
    chatPath: "/brand/chat/positioning",
    editPath: null,
    percentKey: "positioning_percent",
    ready: true,
  },
  {
    number: 8,
    key: "competitors",
    title: "Competitors",
    question: "Who else is playing and how are you different?",
    description:
      "Competitor analysis, differentiation strategy, white space opportunities, and your unique edge.",
    chatPath: "/brand/chat/competitors",
    editPath: null,
    percentKey: "competitors_percent",
    ready: true,
  },
];

export default function BrandDashboard() {
  const [completeness, setCompleteness] = useState<BrandCompleteness | null>(
    null
  );
  const [error, setError] = useState("");

  useEffect(() => {
    brandApi
      .getCompleteness()
      .then(setCompleteness)
      .catch((e) => setError(e.message));
  }, []);

  // Calculate overall across all available stages
  const availableStages = stages.filter((s) => s.percentKey && completeness);
  const overallPercent = completeness?.overall_percent ?? 0;

  return (
    <main className="max-w-4xl mx-auto p-8 bg-background text-card-foreground min-h-screen">
      <h1 className="text-3xl font-bold mb-2 text-card-foreground">Your Personal Brand</h1>
      <p className="text-muted-foreground mb-8">
        Build your brand step by step. Complete each stage in order — each one
        builds on the last.
      </p>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded p-4 mb-6 text-red-400 text-sm">
          {error}
        </div>
      )}

      {completeness && (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm font-medium text-foreground">
              Overall progress
            </span>
            <span className="text-sm text-muted-foreground">{overallPercent}%</span>
          </div>
          <div className="w-full bg-accent rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all"
              style={{ width: `${overallPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Learning Path */}
      <div className="relative">
        {/* Vertical connector line */}
        <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-accent" />

        <div className="space-y-4">
          {stages.map((stage) => {
            const pct = stage.percentKey && completeness
              ? completeness[stage.percentKey]
              : 0;
            const isComplete = pct >= 80;
            const isStarted = pct > 0;

            return (
              <div key={stage.key} className="relative flex gap-4">
                {/* Stage number circle */}
                <div
                  className={`relative z-10 flex items-center justify-center w-12 h-12 rounded-full border-2 text-sm font-bold shrink-0 ${
                    isComplete
                      ? "bg-green-600 border-green-600 text-white"
                      : isStarted
                      ? "bg-yellow-500/20 border-yellow-500 text-yellow-400"
                      : stage.ready
                      ? "bg-card border-border text-muted-foreground"
                      : "bg-card border-border text-muted-foreground"
                  }`}
                >
                  {isComplete ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    stage.number
                  )}
                </div>

                {/* Stage card */}
                <div
                  className={`flex-1 rounded-lg border p-5 ${
                    stage.ready
                      ? "bg-card border-border"
                      : "bg-card/50 border-border/50"
                  }`}
                >
                  <div className="flex items-start justify-between mb-1">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-semibold">{stage.title}</h2>
                        {!stage.ready && (
                          <span className="text-xs bg-accent text-muted-foreground px-2 py-0.5 rounded">
                            Coming soon
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-primary font-medium">
                        {stage.question}
                      </p>
                    </div>
                    {stage.ready && completeness && stage.percentKey && (
                      <span
                        className={`text-sm font-medium px-2 py-1 rounded ${
                          isComplete
                            ? "bg-green-500/20 text-green-400"
                            : isStarted
                            ? "bg-yellow-500/20 text-yellow-400"
                            : "bg-accent text-muted-foreground"
                        }`}
                      >
                        {pct}%
                      </span>
                    )}
                  </div>

                  <p className="text-muted-foreground text-sm mb-3">
                    {stage.description}
                  </p>

                  {stage.ready && stage.percentKey && completeness && (
                    <div className="w-full bg-accent rounded-full h-1.5 mb-4">
                      <div
                        className={`h-1.5 rounded-full transition-all ${
                          isComplete
                            ? "bg-green-500"
                            : isStarted
                            ? "bg-yellow-500"
                            : "bg-muted"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  )}

                  {stage.ready && (
                    <div className="flex gap-3">
                      {stage.chatPath && (
                        <Link
                          href={stage.chatPath}
                          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
                        >
                          {isStarted ? "Continue chat" : "Start with AI"}
                        </Link>
                      )}
                      {stage.editPath && (
                        <Link
                          href={stage.editPath}
                          className="px-4 py-2 border border-border text-foreground rounded-lg text-sm font-medium hover:bg-accent transition"
                        >
                          Edit manually
                        </Link>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
}
