"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { contentApi } from "../../../lib/api";

const PLATFORMS = [
  {
    id: "youtube",
    label: "YouTube",
    description: "Long-form script + 3 Shorts + titles, description, tags, thumbnail brief",
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
      </svg>
    ),
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    description: "3 post variants: story, list, and contrarian angle",
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
      </svg>
    ),
  },
  {
    id: "twitter",
    label: "Twitter/X",
    description: "3 standalone posts + 1 thread",
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    ),
  },
  {
    id: "short_form",
    label: "Short-form",
    description: "TikTok, Reels, and Shorts scripts (30-60 seconds each)",
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="6" y="3" width="12" height="18" rx="2" />
        <line x1="10" y1="17" x2="14" y2="17" />
      </svg>
    ),
  },
];

const RESEARCH_SOURCES = [
  { id: "youtube", label: "YouTube trends" },
  { id: "reddit", label: "Reddit discussions" },
  { id: "newsletters", label: "Newsletters" },
  { id: "news", label: "News" },
  { id: "user_resources", label: "My uploaded resources" },
];

export default function NewWorkflow() {
  const router = useRouter();
  const [goalText, setGoalText] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["youtube"]);
  const [sources, setSources] = useState<Record<string, boolean>>({
    youtube: true,
    reddit: true,
    newsletters: true,
    news: true,
    user_resources: true,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const togglePlatform = (id: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(id)
        ? prev.filter((p) => p !== id)
        : [...prev, id]
    );
  };

  const toggleSource = (id: string) => {
    setSources((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalText.trim() || selectedPlatforms.length === 0) return;

    setSubmitting(true);
    setError("");

    try {
      const result = await contentApi.create({
        goal_text: goalText.trim(),
        platforms: selectedPlatforms,
        settings: { sources },
      });
      router.push(`/content/${result.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create workflow");
      setSubmitting(false);
    }
  };

  return (
    <main className="max-w-2xl mx-auto p-8">
      <Link
        href="/content"
        className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        &larr; Back to Content
      </Link>

      <h1 className="text-3xl font-bold mb-2">New Content</h1>
      <p className="text-gray-600 mb-8">
        Tell the AI what you want to create. It will research, find topics, generate hooks,
        and write the content for your selected platforms.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Goal */}
        <div>
          <label htmlFor="goal" className="block text-sm font-medium text-gray-900 mb-2">
            What do you want to create content about?
          </label>
          <textarea
            id="goal"
            value={goalText}
            onChange={(e) => setGoalText(e.target.value)}
            placeholder="e.g. How to build a personal brand on LinkedIn in 2026, targeting solopreneurs who are stuck at under 1000 followers"
            className="w-full border border-gray-300 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={4}
            maxLength={2000}
            required
          />
          <p className="text-xs text-gray-400 mt-1">
            {goalText.length}/2000 characters. Be specific about the topic, angle, and audience.
          </p>
        </div>

        {/* Platforms */}
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-3">
            Which platforms? (pick at least one)
          </label>
          <div className="grid grid-cols-2 gap-3">
            {PLATFORMS.map((p) => {
              const selected = selectedPlatforms.includes(p.id);
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => togglePlatform(p.id)}
                  className={`flex items-start gap-3 p-4 rounded-lg border-2 text-left transition ${
                    selected
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 bg-white hover:border-gray-300"
                  }`}
                >
                  <div className={`mt-0.5 ${selected ? "text-blue-600" : "text-gray-400"}`}>
                    {p.icon}
                  </div>
                  <div>
                    <div className={`text-sm font-medium ${selected ? "text-blue-900" : "text-gray-900"}`}>
                      {p.label}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">{p.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Research Sources */}
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-3">
            Research sources
          </label>
          <div className="flex flex-wrap gap-2">
            {RESEARCH_SOURCES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => toggleSource(s.id)}
                className={`px-3 py-1.5 rounded-full text-sm border transition ${
                  sources[s.id]
                    ? "border-blue-300 bg-blue-50 text-blue-700"
                    : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            The AI will search these sources for trends, discussions, and content gaps before writing.
          </p>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-4 pt-4">
          <button
            type="submit"
            disabled={submitting || !goalText.trim() || selectedPlatforms.length === 0}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Creating...
              </span>
            ) : (
              "Create Content"
            )}
          </button>
          <Link
            href="/content"
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </Link>
        </div>
      </form>
    </main>
  );
}
