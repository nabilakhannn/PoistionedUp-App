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
    key: "positioning",
    title: "Positioning & Competitors",
    question: "How do you stand out?",
    description:
      "Competitor research, content gap analysis, and your unique perspective.",
    chatPath: null,
    editPath: null,
    percentKey: null,
    ready: false,
  },
  {
    number: 6,
    key: "profile",
    title: "LinkedIn Profile",
    question: "How do you show up?",
    description:
      "17-point profile audit: headline, about section, featured, and more.",
    chatPath: null,
    editPath: null,
    percentKey: null,
    ready: false,
  },
  {
    number: 7,
    key: "content_strategy",
    title: "Content Strategy",
    question: "What will you post?",
    description:
      "Content pillars, Radio Framework balance, calendar, and idea bank.",
    chatPath: null,
    editPath: null,
    percentKey: null,
    ready: false,
  },
  {
    number: 8,
    key: "writing",
    title: "Writing & Hooks",
    question: "How will you write?",
    description:
      "Hook library, writing assistant, post templates, and anti-AI checklist.",
    chatPath: null,
    editPath: null,
    percentKey: null,
    ready: false,
  },
  {
    number: 9,
    key: "authority",
    title: "Authority Building",
    question: "How do you build trust?",
    description:
      "Authority flywheel, framing score, social proof, and signature style.",
    chatPath: null,
    editPath: null,
    percentKey: null,
    ready: false,
  },
  {
    number: 10,
    key: "monetization",
    title: "Growth & Monetization",
    question: "How do you convert?",
    description:
      "DM sequences, engagement strategy, launch planner, and lead generation.",
    chatPath: null,
    editPath: null,
    percentKey: null,
    ready: false,
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
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Your Personal Brand</h1>
      <p className="text-gray-600 mb-8">
        Build your brand step by step. Complete each stage in order — each one
        builds on the last.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      {completeness && (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm font-medium text-gray-700">
              Overall progress
            </span>
            <span className="text-sm text-gray-500">{overallPercent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${overallPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Learning Path */}
      <div className="relative">
        {/* Vertical connector line */}
        <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-gray-200" />

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
                      ? "bg-yellow-50 border-yellow-500 text-yellow-700"
                      : stage.ready
                      ? "bg-white border-gray-300 text-gray-600"
                      : "bg-gray-50 border-gray-200 text-gray-400"
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
                      ? "bg-white border-gray-200"
                      : "bg-gray-50 border-gray-100"
                  }`}
                >
                  <div className="flex items-start justify-between mb-1">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-semibold">{stage.title}</h2>
                        {!stage.ready && (
                          <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">
                            Coming soon
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-blue-600 font-medium">
                        {stage.question}
                      </p>
                    </div>
                    {stage.ready && completeness && stage.percentKey && (
                      <span
                        className={`text-sm font-medium px-2 py-1 rounded ${
                          isComplete
                            ? "bg-green-100 text-green-700"
                            : isStarted
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {pct}%
                      </span>
                    )}
                  </div>

                  <p className="text-gray-500 text-sm mb-3">
                    {stage.description}
                  </p>

                  {stage.ready && stage.percentKey && completeness && (
                    <div className="w-full bg-gray-100 rounded-full h-1.5 mb-4">
                      <div
                        className={`h-1.5 rounded-full transition-all ${
                          isComplete
                            ? "bg-green-500"
                            : isStarted
                            ? "bg-yellow-500"
                            : "bg-gray-300"
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
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
                        >
                          {isStarted ? "Continue chat" : "Start with AI"}
                        </Link>
                      )}
                      {stage.editPath && (
                        <Link
                          href={stage.editPath}
                          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
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
