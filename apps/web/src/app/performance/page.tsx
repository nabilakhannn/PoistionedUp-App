"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  performanceApi,
  ContentPostSummary,
  ContentPostDetail,
  PerformanceAnalytics,
} from "../../lib/api";

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
  viral: "bg-purple-100 text-purple-800",
  above_average: "bg-green-100 text-green-800",
  average: "bg-gray-100 text-gray-800",
  below_average: "bg-yellow-100 text-yellow-800",
  flop: "bg-red-100 text-red-800",
};

export default function PerformancePage() {
  const [posts, setPosts] = useState<ContentPostSummary[]>([]);
  const [analytics, setAnalytics] = useState<PerformanceAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"posts" | "analytics" | "log">("posts");

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

  const loadData = async () => {
    try {
      const [postsData, analyticsData] = await Promise.all([
        performanceApi.list(),
        performanceApi.analytics(),
      ]);
      setPosts(postsData);
      setAnalytics(analyticsData);
      setLoading(false);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

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
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) {
    return (
      <main className="max-w-5xl mx-auto p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-56" />
          <div className="h-4 bg-gray-200 rounded w-80" />
          <div className="flex gap-3 mb-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-9 bg-gray-200 rounded-lg w-24" />
            ))}
          </div>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-5">
                <div className="h-5 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="flex gap-4">
                  <div className="h-3 bg-gray-200 rounded w-20" />
                  <div className="h-3 bg-gray-200 rounded w-16" />
                  <div className="h-3 bg-gray-200 rounded w-24" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Performance Tracker</h1>
          <p className="text-gray-600 mt-1">
            Log published content. Track what works. The AI learns from YOUR
            data.
          </p>
        </div>
        <Link
          href="/"
          className="text-sm text-blue-600 hover:underline"
        >
          Home
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {(["posts", "analytics", "log"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "posts"
              ? `Posts (${posts.length})`
              : t === "analytics"
              ? "Analytics"
              : "+ Log Post"}
          </button>
        ))}
      </div>

      {/* Posts Tab */}
      {tab === "posts" && (
        <div className="space-y-3">
          {posts.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">&#128200;</div>
              <h2 className="text-xl font-semibold mb-2">No posts logged yet</h2>
              <p className="text-gray-500 mb-4">
                Start logging your published content to build your performance
                database.
              </p>
              <button
                onClick={() => setTab("log")}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
              >
                Log your first post
              </button>
            </div>
          ) : (
            posts.map((post) => (
              <div
                key={post.id}
                className="bg-white border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium">{post.title}</h3>
                      {post.performance_tier && (
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            TIER_COLORS[post.performance_tier] || "bg-gray-100"
                          }`}
                        >
                          {post.performance_tier.replace("_", " ")}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span className="bg-gray-100 px-1.5 py-0.5 rounded">
                        {post.platform}
                      </span>
                      <span>{post.content_type.replace("_", " ")}</span>
                      {post.hook_type && <span>Hook: {post.hook_type}</span>}
                      {post.topic_category && (
                        <span>Topic: {post.topic_category}</span>
                      )}
                    </div>
                    {/* Metrics row */}
                    <div className="flex items-center gap-4 text-xs text-gray-500 mt-2">
                      {post.views != null && <span>{post.views.toLocaleString()} views</span>}
                      {post.likes != null && <span>{post.likes.toLocaleString()} likes</span>}
                      {post.comments != null && (
                        <span>{post.comments.toLocaleString()} comments</span>
                      )}
                      {post.engagement_rate != null && (
                        <span className="font-medium text-blue-600">
                          {(post.engagement_rate * 100).toFixed(2)}% ER
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() =>
                        setSelectedPost(
                          selectedPost === post.id ? null : post.id
                        )
                      }
                      className="text-xs text-blue-500 hover:underline"
                    >
                      {selectedPost === post.id ? "Cancel" : "Update Metrics"}
                    </button>
                    <button
                      onClick={() => handleAnalyze(post.id)}
                      className="text-xs text-purple-500 hover:underline"
                    >
                      Analyze
                    </button>
                  </div>
                </div>

                {/* Metrics update form */}
                {selectedPost === post.id && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="grid grid-cols-5 gap-2">
                      <input
                        type="number"
                        placeholder="Views"
                        value={metricsViews}
                        onChange={(e) => setMetricsViews(e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded text-xs"
                      />
                      <input
                        type="number"
                        placeholder="Likes"
                        value={metricsLikes}
                        onChange={(e) => setMetricsLikes(e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded text-xs"
                      />
                      <input
                        type="number"
                        placeholder="Comments"
                        value={metricsComments}
                        onChange={(e) => setMetricsComments(e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded text-xs"
                      />
                      <input
                        type="number"
                        placeholder="Shares"
                        value={metricsShares}
                        onChange={(e) => setMetricsShares(e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded text-xs"
                      />
                      <input
                        type="number"
                        placeholder="Saves"
                        value={metricsSaves}
                        onChange={(e) => setMetricsSaves(e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded text-xs"
                      />
                    </div>
                    <button
                      onClick={handleUpdateMetrics}
                      disabled={updatingMetrics}
                      className="mt-2 px-3 py-1 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition"
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

      {/* Analytics Tab */}
      {tab === "analytics" && analytics && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Overview</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {analytics.total_posts}
                </div>
                <div className="text-xs text-gray-500">Total Posts</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">
                  {analytics.best_day_of_week || "N/A"}
                </div>
                <div className="text-xs text-gray-500">Best Day</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-purple-600">
                  {analytics.patterns.length}
                </div>
                <div className="text-xs text-gray-500">Patterns Found</div>
              </div>
            </div>
          </div>

          {/* Patterns */}
          {analytics.patterns.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Detected Patterns</h2>
              <div className="space-y-3">
                {analytics.patterns.map((p, i) => (
                  <div
                    key={i}
                    className="border border-gray-100 rounded p-3"
                  >
                    <p className="font-medium text-sm">{p.pattern}</p>
                    <p className="text-xs text-gray-500 mt-1">{p.evidence}</p>
                    <div className="mt-1">
                      <span className="text-xs text-gray-400">
                        Confidence: {Math.round(p.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Hooks */}
          {analytics.top_hooks.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Top Hooks</h2>
              <ul className="space-y-2">
                {analytics.top_hooks.map((h, i) => (
                  <li
                    key={i}
                    className="text-sm text-gray-700 italic border-l-2 border-green-400 pl-3"
                  >
                    &ldquo;{h}&rdquo;
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Anti-Hooks */}
          {analytics.anti_hooks.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">
                Hooks That Flopped
              </h2>
              <ul className="space-y-2">
                {analytics.anti_hooks.map((h, i) => (
                  <li
                    key={i}
                    className="text-sm text-gray-500 italic border-l-2 border-red-400 pl-3"
                  >
                    &ldquo;{h}&rdquo;
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Platform Breakdown */}
          {analytics.platforms.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">By Platform</h2>
              <div className="space-y-2">
                {analytics.platforms.map((p) => (
                  <div
                    key={p.platform}
                    className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
                  >
                    <div>
                      <span className="font-medium text-sm capitalize">
                        {p.platform}
                      </span>
                      <span className="text-xs text-gray-400 ml-2">
                        {p.post_count} posts
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {p.avg_engagement_rate != null
                        ? `${(p.avg_engagement_rate * 100).toFixed(2)}% avg ER`
                        : "No metrics"}
                      {p.top_tier_count > 0 && (
                        <span className="ml-2 text-green-600">
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
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">
                Best Topics
              </h2>
              <div className="space-y-2">
                {analytics.top_topics.map((t) => (
                  <div
                    key={t.topic_category}
                    className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
                  >
                    <span className="font-medium text-sm">
                      {t.topic_category}
                    </span>
                    <div className="text-xs text-gray-500">
                      {t.post_count} posts
                      {t.avg_engagement_rate != null &&
                        ` | ${(t.avg_engagement_rate * 100).toFixed(2)}% ER`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Log Post Tab */}
      {tab === "log" && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Log Published Content</h2>
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Post title *"
              value={logTitle}
              onChange={(e) => setLogTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <div className="grid grid-cols-2 gap-3">
              <select
                value={logPlatform}
                onChange={(e) => setLogPlatform(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <div className="grid grid-cols-2 gap-3">
              <select
                value={logHookType}
                onChange={(e) => setLogHookType(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                placeholder="Topic category (ai_tools, business, etc.)"
                value={logTopicCategory}
                onChange={(e) => setLogTopicCategory(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <input
              type="text"
              placeholder="Published URL (optional)"
              value={logUrl}
              onChange={(e) => setLogUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <button
              onClick={handleLogPost}
              disabled={creating || !logTitle.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {creating ? "Logging..." : "Log Post"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
