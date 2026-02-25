"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  performanceApi,
  voiceApi,
  ContentPostSummary,
  PerformanceAnalytics,
  SelfVoiceDNA,
  VoiceDriftResult,
} from "../../lib/api";
import { useBrand } from "@/lib/brand-context";
import { trackEvent } from "@/lib/posthog";

const PLATFORMS = ["youtube", "linkedin", "instagram", "twitter", "tiktok"];
const CONTENT_TYPES = [
  "youtube_long",
  "youtube_short",
  "linkedin_post",
  "twitter_thread",
  "instagram_reel",
  "tiktok_video",
  "blog_post",
];
const HOOK_TYPES = [
  "question",
  "bold_claim",
  "story",
  "statistic",
  "contrarian",
  "curiosity",
  "challenge",
];
const DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

const TIER_COLORS: Record<string, string> = {
  viral: "bg-purple-500/20 text-purple-300 border border-purple-500/30",
  above_average: "bg-green-500/20 text-green-300 border border-green-500/30",
  average: "bg-zinc-700 text-zinc-300 border border-zinc-600",
  below_average: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
  flop: "bg-red-500/20 text-red-300 border border-red-500/30",
};

const DRIFT_LEVEL_COLORS: Record<string, string> = {
  none: "text-green-400",
  low: "text-green-400",
  moderate: "text-yellow-400",
  high: "text-red-400",
  critical: "text-red-500",
};

/* ── Stat Card ────────────────────────────────── */
function StatCard({
  label,
  value,
  color = "text-blue-400",
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="bg-zinc-800/60 border border-zinc-700 rounded-xl p-4 text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-zinc-400 mt-1">{label}</div>
    </div>
  );
}

/* ── Drift Gauge ────────────────────────────────── */
function DriftGauge({ score, level }: { score: number; level: string }) {
  const pct = Math.min(score * 100, 100);
  const color =
    pct <= 25
      ? "bg-green-500"
      : pct <= 50
      ? "bg-yellow-500"
      : pct <= 75
      ? "bg-orange-500"
      : "bg-red-500";

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-400">Voice Drift</span>
        <span className={DRIFT_LEVEL_COLORS[level] || "text-zinc-300"}>
          {level.charAt(0).toUpperCase() + level.slice(1)} ({pct.toFixed(0)}%)
        </span>
      </div>
      <div className="w-full h-3 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/* ── Main Page ────────────────────────────────── */
export default function PerformancePage() {
  const { brandId, loading: brandLoading } = useBrand();
  const [posts, setPosts] = useState<ContentPostSummary[]>([]);
  const [analytics, setAnalytics] = useState<PerformanceAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"posts" | "analytics" | "voice" | "log">("posts");

  // Voice drift state
  const [voiceBaseline, setVoiceBaseline] = useState<SelfVoiceDNA | null>(null);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const [analyzingSelf, setAnalyzingSelf] = useState(false);
  const [driftText, setDriftText] = useState("");
  const [driftResult, setDriftResult] = useState<VoiceDriftResult | null>(null);
  const [checkingDrift, setCheckingDrift] = useState(false);

  // Log form state
  const [logTitle, setLogTitle] = useState("");
  const [logPlatform, setLogPlatform] = useState("youtube");
  const [logContentType, setLogContentType] = useState("youtube_long");
  const [logHookUsed, setLogHookUsed] = useState("");
  const [logHookType, setLogHookType] = useState("");
  const [logTopic, setLogTopic] = useState("");
  const [logTopicCategory, setLogTopicCategory] = useState("");
  const [logUrl, setLogUrl] = useState("");
  const [logDay, setLogDay] = useState("");
  const [creating, setCreating] = useState(false);

  // Metrics update
  const [selectedPost, setSelectedPost] = useState<string | null>(null);
  const [metricsViews, setMetricsViews] = useState("");
  const [metricsLikes, setMetricsLikes] = useState("");
  const [metricsComments, setMetricsComments] = useState("");
  const [metricsShares, setMetricsShares] = useState("");
  const [metricsSaves, setMetricsSaves] = useState("");
  const [updatingMetrics, setUpdatingMetrics] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [postsData, analyticsData] = await Promise.all([
        performanceApi.list(undefined, undefined, brandId || undefined),
        performanceApi.analytics(brandId || undefined),
      ]);
      setPosts(postsData);
      setAnalytics(analyticsData);
      setLoading(false);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  }, [brandId]);

  const loadVoiceBaseline = useCallback(async () => {
    setVoiceLoading(true);
    setVoiceError("");
    try {
      const baseline = await voiceApi.getBaseline(brandId || undefined);
      setVoiceBaseline(baseline);
    } catch (e: any) {
      // 404 is fine, means no baseline yet
      if (!e.message?.includes("404")) {
        setVoiceError(e.message);
      }
    } finally {
      setVoiceLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    if (brandLoading) return;
    loadData();
  }, [brandId, brandLoading, loadData]);

  useEffect(() => {
    if (tab === "voice" && !voiceBaseline && !voiceLoading) {
      loadVoiceBaseline();
    }
  }, [tab, voiceBaseline, voiceLoading, loadVoiceBaseline]);

  const handleAnalyzeSelf = async () => {
    setAnalyzingSelf(true);
    setVoiceError("");
    try {
      const result = await voiceApi.analyzeSelf(brandId || undefined);
      setVoiceBaseline(result.voice_dna);
      trackEvent("voice_self_analyzed", { brand_id: brandId || "" });
    } catch (e: any) {
      setVoiceError(e.message);
    } finally {
      setAnalyzingSelf(false);
    }
  };

  const handleCheckDrift = async () => {
    if (!driftText.trim()) return;
    setCheckingDrift(true);
    setVoiceError("");
    try {
      const result = await voiceApi.checkDrift(driftText.trim(), brandId || undefined);
      setDriftResult(result);
      trackEvent("voice_drift_checked", {
        drift_level: result.drift_level,
        brand_id: brandId || "",
      });
    } catch (e: any) {
      setVoiceError(e.message);
    } finally {
      setCheckingDrift(false);
    }
  };

  const handleLogPost = async () => {
    if (!logTitle.trim()) return;
    setCreating(true);
    setError("");
    try {
      await performanceApi.create({
        title: logTitle.trim(),
        content_type: logContentType,
        platform: logPlatform,
        hook_used: logHookUsed.trim() || undefined,
        hook_type: logHookType || undefined,
        topic: logTopic.trim() || undefined,
        topic_category: logTopicCategory.trim() || undefined,
        published_url: logUrl.trim() || undefined,
        day_of_week: logDay || undefined,
        brand_id: brandId || undefined,
      });
      trackEvent("performance_post_logged", {
        platform: logPlatform,
        content_type: logContentType,
        hook_type: logHookType || "",
        brand_id: brandId || "",
      });
      setLogTitle("");
      setLogHookUsed("");
      setLogHookType("");
      setLogTopic("");
      setLogTopicCategory("");
      setLogUrl("");
      setLogDay("");
      setTab("posts");
      loadData();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateMetrics = async () => {
    if (!selectedPost) return;
    setUpdatingMetrics(true);
    setError("");
    try {
      const data: Record<string, number> = {};
      if (metricsViews) data.views = parseInt(metricsViews);
      if (metricsLikes) data.likes = parseInt(metricsLikes);
      if (metricsComments) data.comments = parseInt(metricsComments);
      if (metricsShares) data.shares = parseInt(metricsShares);
      if (metricsSaves) data.saves = parseInt(metricsSaves);

      if (Object.keys(data).length === 0) {
        setError("Enter at least one metric");
        setUpdatingMetrics(false);
        return;
      }

      await performanceApi.updateMetrics(selectedPost, data);
      trackEvent("performance_metrics_updated", {
        post_id: selectedPost,
        brand_id: brandId || "",
      });
      setSelectedPost(null);
      setMetricsViews("");
      setMetricsLikes("");
      setMetricsComments("");
      setMetricsShares("");
      setMetricsSaves("");
      loadData();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUpdatingMetrics(false);
    }
  };

  const handleAnalyze = async (postId: string) => {
    try {
      await performanceApi.analyze(postId);
      trackEvent("performance_post_analyzed", {
        post_id: postId,
        brand_id: brandId || "",
      });
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  /* ── Loading Skeleton (dark) ────────────────────── */
  if (loading) {
    return (
      <main className="min-h-screen bg-zinc-950 text-zinc-100">
        <div className="max-w-5xl mx-auto p-8 animate-pulse space-y-6">
          <div className="h-8 bg-zinc-800 rounded w-56" />
          <div className="h-4 bg-zinc-800 rounded w-80" />
          <div className="flex gap-3 mb-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-9 bg-zinc-800 rounded-lg w-24" />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-zinc-800/60 border border-zinc-700 rounded-xl p-6 h-24" />
            ))}
          </div>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
                <div className="h-5 bg-zinc-800 rounded w-3/4 mb-2" />
                <div className="flex gap-4">
                  <div className="h-3 bg-zinc-800 rounded w-20" />
                  <div className="h-3 bg-zinc-800 rounded w-16" />
                  <div className="h-3 bg-zinc-800 rounded w-24" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    );
  }

  const tabs = [
    { key: "posts" as const, label: `Posts (${posts.length})` },
    { key: "analytics" as const, label: "Analytics" },
    { key: "voice" as const, label: "Voice DNA" },
    { key: "log" as const, label: "+ Log Post" },
  ];

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-5xl mx-auto p-8">
        {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Performance Tracker</h1>
            <p className="text-zinc-400 mt-1">
              Log published content. Track what works. The AI learns from YOUR data.
          </p>
        </div>
          <Link href="/" className="text-sm text-blue-400 hover:text-blue-300 transition">
          Home
        </Link>
      </div>

        {/* Error Banner */}
      {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-300 text-sm">
          {error}
            <button
              onClick={() => setError("")}
              className="ml-3 text-red-400 hover:text-red-200 transition"
            >
              Dismiss
            </button>
        </div>
      )}

      {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-zinc-800">
          {tabs.map((t) => (
          <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${
                tab === t.key
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {t.label}
          </button>
        ))}
      </div>

        {/* ── Posts Tab ────────────────────────────── */}
      {tab === "posts" && (
        <div className="space-y-3">
          {posts.length === 0 ? (
              <div className="text-center py-16">
                <div className="text-5xl mb-4">📊</div>
                <h2 className="text-xl font-semibold mb-2 text-zinc-200">
                  No posts logged yet
                </h2>
                <p className="text-zinc-500 mb-6 max-w-md mx-auto">
                Start logging your published content to build your performance
                  database. The AI learns from your real data to improve future content.
              </p>
              <button
                onClick={() => setTab("log")}
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition"
              >
                Log your first post
              </button>
            </div>
          ) : (
            posts.map((post) => (
              <div
                key={post.id}
                  className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-zinc-100">{post.title}</h3>
                      {post.performance_tier && (
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                              TIER_COLORS[post.performance_tier] || "bg-zinc-700 text-zinc-300"
                          }`}
                        >
                          {post.performance_tier.replace("_", " ")}
                        </span>
                      )}
                    </div>
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span className="bg-zinc-800 px-1.5 py-0.5 rounded capitalize">
                        {post.platform}
                      </span>
                      <span>{post.content_type.replace("_", " ")}</span>
                      {post.hook_type && <span>Hook: {post.hook_type}</span>}
                      {post.topic_category && (
                        <span>Topic: {post.topic_category}</span>
                      )}
                    </div>
                    {/* Metrics row */}
                      <div className="flex items-center gap-4 text-xs text-zinc-400 mt-2">
                        {post.views != null && (
                          <span>{post.views.toLocaleString()} views</span>
                        )}
                        {post.likes != null && (
                          <span>{post.likes.toLocaleString()} likes</span>
                        )}
                      {post.comments != null && (
                        <span>{post.comments.toLocaleString()} comments</span>
                      )}
                      {post.engagement_rate != null && (
                          <span className="font-medium text-blue-400">
                          {(post.engagement_rate * 100).toFixed(2)}% ER
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() =>
                          setSelectedPost(selectedPost === post.id ? null : post.id)
                      }
                        className="text-xs text-blue-400 hover:text-blue-300 transition"
                    >
                      {selectedPost === post.id ? "Cancel" : "Update Metrics"}
                    </button>
                    <button
                      onClick={() => handleAnalyze(post.id)}
                        className="text-xs text-purple-400 hover:text-purple-300 transition"
                    >
                      Analyze
                    </button>
                  </div>
                </div>

                {/* Metrics update form */}
                {selectedPost === post.id && (
                    <div className="mt-3 pt-3 border-t border-zinc-800">
                    <div className="grid grid-cols-5 gap-2">
                        {[
                          { label: "Views", val: metricsViews, set: setMetricsViews },
                          { label: "Likes", val: metricsLikes, set: setMetricsLikes },
                          { label: "Comments", val: metricsComments, set: setMetricsComments },
                          { label: "Shares", val: metricsShares, set: setMetricsShares },
                          { label: "Saves", val: metricsSaves, set: setMetricsSaves },
                        ].map((m) => (
                      <input
                            key={m.label}
                        type="number"
                            placeholder={m.label}
                            value={m.val}
                            onChange={(e) => m.set(e.target.value)}
                            className="px-2 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        ))}
                    </div>
                    <button
                      onClick={handleUpdateMetrics}
                      disabled={updatingMetrics}
                        className="mt-2 px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-500 disabled:opacity-50 transition"
                    >
                      {updatingMetrics ? "Saving..." : "Save Metrics"}
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

        {/* ── Analytics Tab ────────────────────────────── */}
      {tab === "analytics" && analytics && (
        <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4">
              <StatCard
                label="Total Posts"
                value={analytics.total_posts}
                color="text-blue-400"
              />
              <StatCard
                label="Best Day"
                value={analytics.best_day_of_week || "N/A"}
                color="text-green-400"
              />
              <StatCard
                label="Patterns Found"
                value={analytics.patterns.length}
                color="text-purple-400"
              />
                </div>

            {/* Detected Patterns */}
            {analytics.patterns.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-zinc-100">
                  Detected Patterns
                </h2>
                <div className="space-y-3">
                  {analytics.patterns.map((p, i) => (
                    <div
                      key={i}
                      className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-3"
                    >
                      <p className="font-medium text-sm text-zinc-200">{p.pattern}</p>
                      <p className="text-xs text-zinc-400 mt-1">{p.evidence}</p>
                      <div className="mt-1.5">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 rounded-full"
                              style={{ width: `${Math.round(p.confidence * 100)}%` }}
                            />
              </div>
                          <span className="text-xs text-zinc-500">
                            {Math.round(p.confidence * 100)}%
                          </span>
                </div>
              </div>
                </div>
                  ))}
              </div>
            </div>
            )}

            {/* Hook Type Breakdown */}
            {analytics.top_hook_types && analytics.top_hook_types.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-zinc-100">
                  Hook Type Performance
                </h2>
              <div className="space-y-3">
                  {analytics.top_hook_types.map((h) => (
                    <div
                      key={h.hook_type}
                      className="flex items-center justify-between py-2 border-b border-zinc-800 last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-zinc-200 capitalize">
                          {h.hook_type.replace("_", " ")}
                        </span>
                        <span className="text-xs text-zinc-500">
                          {h.post_count} post{h.post_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                      <div className="flex items-center gap-3">
                        {h.avg_engagement_rate != null && (
                          <span className="text-xs text-blue-400 font-medium">
                            {(h.avg_engagement_rate * 100).toFixed(2)}% avg ER
                          </span>
                        )}
                        {h.example_hooks && h.example_hooks.length > 0 && (
                          <span className="text-xs text-zinc-500">
                            e.g. &ldquo;{h.example_hooks[0].slice(0, 40)}{h.example_hooks[0].length > 40 ? "..." : ""}&rdquo;
                          </span>
                        )}
                      </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Hooks */}
          {analytics.top_hooks.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-zinc-100">
                  Top Performing Hooks
                </h2>
              <ul className="space-y-2">
                {analytics.top_hooks.map((h, i) => (
                  <li
                    key={i}
                      className="text-sm text-zinc-300 italic border-l-2 border-green-500 pl-3"
                  >
                    &ldquo;{h}&rdquo;
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Anti-Hooks */}
          {analytics.anti_hooks.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-zinc-100">
                Hooks That Flopped
              </h2>
              <ul className="space-y-2">
                {analytics.anti_hooks.map((h, i) => (
                  <li
                    key={i}
                      className="text-sm text-zinc-500 italic border-l-2 border-red-500 pl-3"
                  >
                    &ldquo;{h}&rdquo;
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Platform Breakdown */}
          {analytics.platforms.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-zinc-100">
                  By Platform
                </h2>
              <div className="space-y-2">
                {analytics.platforms.map((p) => (
                  <div
                    key={p.platform}
                      className="flex items-center justify-between py-2.5 border-b border-zinc-800 last:border-0"
                  >
                    <div>
                        <span className="font-medium text-sm capitalize text-zinc-200">
                        {p.platform}
                      </span>
                        <span className="text-xs text-zinc-500 ml-2">
                        {p.post_count} posts
                      </span>
                    </div>
                      <div className="text-xs text-zinc-400">
                      {p.avg_engagement_rate != null
                        ? `${(p.avg_engagement_rate * 100).toFixed(2)}% avg ER`
                        : "No metrics"}
                      {p.top_tier_count > 0 && (
                          <span className="ml-2 text-green-400">
                          {p.top_tier_count} top performers
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Topics */}
          {analytics.top_topics.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-zinc-100">
                Best Topics
              </h2>
              <div className="space-y-2">
                {analytics.top_topics.map((t) => (
                  <div
                    key={t.topic_category}
                      className="flex items-center justify-between py-2.5 border-b border-zinc-800 last:border-0"
                  >
                      <span className="font-medium text-sm text-zinc-200">
                      {t.topic_category}
                    </span>
                      <div className="text-xs text-zinc-400">
                      {t.post_count} posts
                      {t.avg_engagement_rate != null &&
                        ` | ${(t.avg_engagement_rate * 100).toFixed(2)}% ER`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

            {/* Empty analytics */}
            {analytics.total_posts === 0 && (
              <div className="text-center py-12">
                <div className="text-4xl mb-3">📈</div>
                <p className="text-zinc-400">
                  Log some posts first to see analytics. Click the &quot;+ Log Post&quot; tab to get started.
                </p>
              </div>
            )}
        </div>
      )}

        {/* ── Voice DNA Tab ────────────────────────────── */}
        {tab === "voice" && (
          <div className="space-y-6">
            {voiceError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-300 text-sm">
                {voiceError}
                <button
                  onClick={() => setVoiceError("")}
                  className="ml-3 text-red-400 hover:text-red-200 transition"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Voice Baseline */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-zinc-100">
                  Your Voice DNA
                </h2>
                <button
                  onClick={handleAnalyzeSelf}
                  disabled={analyzingSelf}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition"
                >
                  {analyzingSelf
                    ? "Analyzing..."
                    : voiceBaseline
                    ? "Re-analyze Voice"
                    : "Analyze My Voice"}
                </button>
              </div>

              {voiceLoading && (
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-zinc-800 rounded w-1/3" />
                  <div className="h-4 bg-zinc-800 rounded w-1/2" />
                  <div className="h-4 bg-zinc-800 rounded w-2/5" />
                </div>
              )}

              {!voiceLoading && !voiceBaseline && (
                <div className="text-center py-8">
                  <div className="text-4xl mb-3">🎙️</div>
                  <p className="text-zinc-400 max-w-md mx-auto">
                    No voice baseline yet. Click &quot;Analyze My Voice&quot; to extract your
                    unique writing DNA from your approved content. You need at least 3
                    published posts logged for a meaningful analysis.
                  </p>
                </div>
              )}

              {voiceBaseline && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-3">
                      <div className="text-xs text-zinc-500 mb-1">Tone</div>
                      <div className="text-sm font-medium text-zinc-200">
                        {voiceBaseline.tone}
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-3">
                      <div className="text-xs text-zinc-500 mb-1">Sentence Style</div>
                      <div className="text-sm font-medium text-zinc-200">
                        {voiceBaseline.sentence_style}
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-3">
                      <div className="text-xs text-zinc-500 mb-1">Vocabulary</div>
                      <div className="text-sm font-medium text-zinc-200">
                        {voiceBaseline.vocabulary_level}
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-3">
                      <div className="text-xs text-zinc-500 mb-1">Avg Sentence Length</div>
                      <div className="text-sm font-medium text-zinc-200">
                        {voiceBaseline.avg_sentence_length ?? "N/A"} words
                      </div>
                    </div>
                  </div>

                  <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-3">
                    <div className="text-xs text-zinc-500 mb-1">Content Structure</div>
                    <div className="text-sm text-zinc-300">
                      {voiceBaseline.content_structure}
                    </div>
                  </div>

                  {voiceBaseline.personality_traits.length > 0 && (
                    <div>
                      <div className="text-xs text-zinc-500 mb-2">Personality Traits</div>
                      <div className="flex flex-wrap gap-2">
                        {voiceBaseline.personality_traits.map((t, i) => (
                          <span
                            key={i}
                            className="bg-purple-500/15 text-purple-300 border border-purple-500/20 text-xs px-2.5 py-1 rounded-full"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {voiceBaseline.signature_phrases.length > 0 && (
                    <div>
                      <div className="text-xs text-zinc-500 mb-2">Signature Phrases</div>
                      <div className="space-y-1">
                        {voiceBaseline.signature_phrases.map((p, i) => (
                          <div
                            key={i}
                            className="text-sm text-zinc-300 italic border-l-2 border-blue-500 pl-3"
                          >
                            &ldquo;{p}&rdquo;
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {voiceBaseline.hook_patterns.length > 0 && (
                    <div>
                      <div className="text-xs text-zinc-500 mb-2">Hook Patterns</div>
                      <div className="flex flex-wrap gap-2">
                        {voiceBaseline.hook_patterns.map((p, i) => (
                          <span
                            key={i}
                            className="bg-green-500/15 text-green-300 border border-green-500/20 text-xs px-2.5 py-1 rounded-full"
                          >
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {voiceBaseline.sample_hooks.length > 0 && (
                    <div>
                      <div className="text-xs text-zinc-500 mb-2">Sample Hooks</div>
                      <div className="space-y-1">
                        {voiceBaseline.sample_hooks.map((h, i) => (
                          <div
                            key={i}
                            className="text-sm text-zinc-300 italic border-l-2 border-yellow-500 pl-3"
                          >
                            &ldquo;{h}&rdquo;
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="text-xs text-zinc-600 pt-2">
                    Based on {voiceBaseline.posts_analyzed} analyzed post{voiceBaseline.posts_analyzed !== 1 ? "s" : ""}
                  </div>
                </div>
              )}
            </div>

            {/* Voice Drift Check */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4 text-zinc-100">
                Voice Drift Check
              </h2>
              <p className="text-sm text-zinc-400 mb-4">
                Paste any draft content below to check if it matches your voice
                baseline. The AI will score how much it drifts from your natural style.
              </p>

              <textarea
                value={driftText}
                onChange={(e) => setDriftText(e.target.value)}
                placeholder="Paste your draft content here to check for voice drift..."
                rows={5}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              />

              <button
                onClick={handleCheckDrift}
                disabled={checkingDrift || !driftText.trim() || !voiceBaseline}
                className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition"
              >
                {checkingDrift ? "Checking..." : "Check Drift"}
              </button>
              {!voiceBaseline && (
                <span className="text-xs text-zinc-500 ml-3">
                  Analyze your voice first to enable drift checking
                </span>
              )}

              {/* Drift Result */}
              {driftResult && (
                <div className="mt-4 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 space-y-3">
                  <DriftGauge score={driftResult.drift_score} level={driftResult.drift_level} />

                  {driftResult.details.length > 0 && (
                    <div>
                      <div className="text-xs text-zinc-500 mb-2">Details</div>
                      <ul className="space-y-1">
                        {driftResult.details.map((d, i) => (
                          <li key={i} className="text-sm text-zinc-300 flex items-start gap-2">
                            <span className="text-zinc-600 mt-0.5">&#8226;</span>
                            {d}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {driftResult.recommendation && (
                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                      <div className="text-xs text-blue-400 mb-1">Recommendation</div>
                      <p className="text-sm text-zinc-300">{driftResult.recommendation}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Log Post Tab ────────────────────────────── */}
      {tab === "log" && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4 text-zinc-100">
              Log Published Content
            </h2>
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Post title *"
              value={logTitle}
              onChange={(e) => setLogTitle(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <div className="grid grid-cols-2 gap-3">
              <select
                value={logPlatform}
                onChange={(e) => setLogPlatform(e.target.value)}
                  className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>

              <select
                value={logContentType}
                onChange={(e) => setLogContentType(e.target.value)}
                  className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {CONTENT_TYPES.map((ct) => (
                  <option key={ct} value={ct}>
                    {ct.replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>

            <input
              type="text"
              placeholder="Hook used (the actual opening text)"
              value={logHookUsed}
              onChange={(e) => setLogHookUsed(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <div className="grid grid-cols-2 gap-3">
              <select
                value={logHookType}
                onChange={(e) => setLogHookType(e.target.value)}
                  className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Hook type (optional)</option>
                {HOOK_TYPES.map((ht) => (
                  <option key={ht} value={ht}>
                    {ht.replace("_", " ")}
                  </option>
                ))}
              </select>

              <select
                value={logDay}
                onChange={(e) => setLogDay(e.target.value)}
                  className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Day of week (optional)</option>
                {DAYS.map((d) => (
                  <option key={d} value={d}>
                    {d.charAt(0).toUpperCase() + d.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Topic"
                value={logTopic}
                onChange={(e) => setLogTopic(e.target.value)}
                  className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                placeholder="Topic category (ai_tools, business, etc.)"
                value={logTopicCategory}
                onChange={(e) => setLogTopicCategory(e.target.value)}
                  className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <input
              type="text"
              placeholder="Published URL (optional)"
              value={logUrl}
              onChange={(e) => setLogUrl(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <button
              onClick={handleLogPost}
              disabled={creating || !logTitle.trim()}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition"
            >
              {creating ? "Logging..." : "Log Post"}
            </button>
          </div>
        </div>
      )}
      </div>
    </main>
  );
}
