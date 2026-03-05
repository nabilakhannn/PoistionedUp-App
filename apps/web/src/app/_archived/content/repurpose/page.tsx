"use client";

import { useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import {
  repurposeApi,
  RepurposedItem,
  SOURCE_PLATFORMS,
  TARGET_PLATFORMS,
} from "@/lib/api/repurpose";
import { CarouselPreview } from "../components/carousel-preview";
import { AdCopyPreview } from "../components/ad-copy-preview";

export default function RepurposePage() {
  const { brandId } = useBrand();

  const [sourceText, setSourceText] = useState("");
  const [sourcePlatform, setSourcePlatform] = useState("youtube");
  const [targets, setTargets] = useState<string[]>(["linkedin", "twitter"]);
  const [autoSchedule, setAutoSchedule] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<RepurposedItem[]>([]);
  const [scheduledCount, setScheduledCount] = useState(0);

  const toggleTarget = (value: string) => {
    setTargets((prev) =>
      prev.includes(value)
        ? prev.filter((t) => t !== value)
        : [...prev, value]
    );
  };

  const handleRepurpose = async () => {
    if (!sourceText.trim()) {
      setError("Please enter some content to repurpose.");
      return;
    }
    if (targets.length === 0) {
      setError("Select at least one target platform.");
      return;
    }

    setLoading(true);
    setError("");
    setResults([]);
    setScheduledCount(0);

    try {
      const res = await repurposeApi.repurpose({
        source_text: sourceText,
        source_platform: sourcePlatform,
        target_platforms: targets,
        brand_id: brandId || undefined,
        auto_schedule: autoSchedule,
      });
      setResults(res.repurposed);
      setScheduledCount(res.scheduled_items_created);
    } catch (err: any) {
      setError(err.message || "Failed to repurpose content.");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* fallback: do nothing */
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <div className="border-b border-zinc-800 px-6 py-4">
        <div className="flex items-center gap-3">
          <Link
            href="/content"
            className="text-zinc-400 hover:text-white transition-colors"
          >
            Content
          </Link>
          <span className="text-zinc-600">/</span>
          <h1 className="text-lg font-semibold">Repurpose</h1>
        </div>
        <p className="text-sm text-zinc-400 mt-1">
          Turn one piece of content into posts for every platform.
        </p>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Source Input */}
        <section className="space-y-3">
          <label className="text-sm font-medium text-zinc-300">
            Source Content
          </label>
          <textarea
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            rows={8}
            placeholder="Paste your content here (YouTube script, LinkedIn post, blog draft, etc.)"
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-y"
          />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-500">Source platform:</span>
              <select
                value={sourcePlatform}
                onChange={(e) => setSourcePlatform(e.target.value)}
                className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-xs text-white"
              >
                {SOURCE_PLATFORMS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <span className="text-xs text-zinc-500">
              {sourceText.length.toLocaleString()} characters
            </span>
          </div>
        </section>

        {/* Target Platforms */}
        <section className="space-y-3">
          <label className="text-sm font-medium text-zinc-300">
            Repurpose Into
          </label>
          <div className="flex flex-wrap gap-2">
            {TARGET_PLATFORMS.map((p) => (
              <button
                key={p.value}
                onClick={() => toggleTarget(p.value)}
                className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
                  targets.includes(p.value)
                    ? "border-blue-500 bg-blue-500/20 text-blue-300"
                    : "border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-500"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </section>

        {/* Options */}
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-zinc-400">
            <input
              type="checkbox"
              checked={autoSchedule}
              onChange={(e) => setAutoSchedule(e.target.checked)}
              className="rounded bg-zinc-800 border-zinc-600"
            />
            Auto-add to schedule as drafts
          </label>
        </div>

        {/* Action */}
        <button
          onClick={handleRepurpose}
          disabled={loading || !sourceText.trim() || targets.length === 0}
          className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 font-medium text-sm transition-colors"
        >
          {loading ? "Repurposing..." : `Repurpose into ${targets.length} platform${targets.length !== 1 ? "s" : ""}`}
        </button>

        {/* Error */}
        {error && (
          <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Scheduled notification */}
        {scheduledCount > 0 && (
          <div className="px-4 py-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm">
            {scheduledCount} item{scheduledCount !== 1 ? "s" : ""} added to your{" "}
            <Link href="/schedule" className="underline">
              schedule
            </Link>{" "}
            as drafts.
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <section className="space-y-4">
            <h2 className="text-sm font-medium text-zinc-300">
              Repurposed Content ({results.length})
            </h2>
            <div className="space-y-4">
              {results.map((item, i) => {
                if (item.content_type === "carousel") {
                  return (
                    <CarouselPreview
                      key={i}
                      item={item}
                      onCopy={() => copyToClipboard(item.body)}
                    />
                  );
                }
                if (item.content_type === "ad_copy") {
                  return (
                    <AdCopyPreview
                      key={i}
                      item={item}
                      onCopy={() => copyToClipboard(item.body)}
                    />
                  );
                }
                return (
                  <div
                    key={i}
                    className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-xs rounded bg-zinc-800 text-zinc-300">
                          {item.platform}
                        </span>
                        <span className="text-sm font-medium text-white">
                          {item.title}
                        </span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(item.body)}
                        className="text-xs text-zinc-400 hover:text-white transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                    <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-sans leading-relaxed">
                      {item.body}
                    </pre>
                    {item.metadata?.hashtags?.length > 0 && (
                      <p className="text-xs text-blue-400">
                        {item.metadata.hashtags.join(" ")}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
