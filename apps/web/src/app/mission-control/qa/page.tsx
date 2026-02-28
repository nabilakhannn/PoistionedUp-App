"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  qaApi,
  QAReviewOut,
  QAReviewResult,
  QAStats,
  VERDICT_STYLES,
} from "@/lib/api/qa";
import { ScoreBadge } from "./components/score-badge";
import { ReviewDetail } from "./components/review-detail";
import { MC_SUB_NAV } from "../constants";

export default function QADashboardPage() {
  const [stats, setStats] = useState<QAStats | null>(null);
  const [reviews, setReviews] = useState<QAReviewOut[]>([]);
  const [selectedReview, setSelectedReview] = useState<QAReviewResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [verdictFilter, setVerdictFilter] = useState<string | undefined>(undefined);

  const loadData = useCallback(async () => {
    try {
      const [statsData, reviewsData] = await Promise.all([
        qaApi.stats(30),
        qaApi.list({ days: 30, verdict: verdictFilter, limit: 50 }),
      ]);
      setStats(statsData);
      setReviews(reviewsData);
    } catch (e) {
      console.error("Failed to load QA data:", e);
    } finally {
      setLoading(false);
    }
  }, [verdictFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadReviewDetail = async (id: string) => {
    try {
      const detail = await qaApi.get(id);
      setSelectedReview(detail);
    } catch (e) {
      console.error("Failed to load review detail:", e);
    }
  };

  const passRate = stats && stats.total_reviews > 0
    ? Math.round((stats.pass_count / stats.total_reviews) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Sub-nav */}
      <div className="flex items-center gap-1 flex-wrap">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control/qa"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Content QA Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track content quality scores, common issues, and review history.
        </p>
      </div>

      {loading ? (
        <div className="text-center text-muted-foreground py-12">Loading QA data...</div>
      ) : (
        <div className="space-y-6">
          {/* Stats Row */}
          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
                <span className="text-xs text-muted-foreground block">Total Reviews</span>
                <span className="text-2xl font-bold">{stats.total_reviews}</span>
              </div>
              <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
                <span className="text-xs text-muted-foreground block">Pass Rate</span>
                <span className={`text-2xl font-bold ${passRate >= 70 ? "text-green-400" : passRate >= 40 ? "text-yellow-400" : "text-red-400"}`}>
                  {passRate}%
                </span>
              </div>
              <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
                <span className="text-xs text-muted-foreground block">Avg Score</span>
                <span className="text-2xl font-bold">{stats.avg_score.toFixed(0)}</span>
              </div>
              <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
                <span className="text-xs text-muted-foreground block">Needs Revision</span>
                <span className="text-2xl font-bold text-yellow-400">{stats.revise_count}</span>
              </div>
            </div>
          )}

          {/* Score Averages */}
          {stats && stats.total_reviews > 0 && (
            <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
              <h3 className="text-sm font-semibold mb-3">Average Dimension Scores</h3>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <span className="text-xs text-muted-foreground block">Voice</span>
                  <span className="text-lg font-bold">{stats.avg_voice_score.toFixed(0)}</span>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground block">Hook</span>
                  <span className="text-lg font-bold">{stats.avg_hook_score.toFixed(0)}</span>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground block">Virality</span>
                  <span className="text-lg font-bold">{stats.avg_virality_score.toFixed(0)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Common Issues */}
          {stats && stats.common_issues.length > 0 && (
            <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
              <h3 className="text-sm font-semibold mb-3">
                Common Issues ({stats.common_issues.length})
              </h3>
              <div className="space-y-2">
                {stats.common_issues.slice(0, 5).map((issue) => (
                  <div key={issue.category} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground capitalize">{issue.category.replace("_", " ")}</span>
                    <span className="font-medium">{issue.count} occurrences</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Verdict Filter */}
          <div className="flex gap-2">
            {[undefined, "pass", "revise", "fail"].map((v) => (
              <button
                key={v || "all"}
                onClick={() => { setVerdictFilter(v); setLoading(true); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                  verdictFilter === v
                    ? "bg-primary/10 text-primary border-primary/30"
                    : "text-muted-foreground border-zinc-800 hover:border-zinc-600"
                }`}
              >
                {v ? v.charAt(0).toUpperCase() + v.slice(1) : "All"}
              </button>
            ))}
          </div>

          {/* Reviews Table */}
          {reviews.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-zinc-800 rounded-lg">
              <p className="text-muted-foreground">No QA reviews yet.</p>
              <p className="text-xs text-muted-foreground mt-1">
                Reviews appear here when content is submitted for quality checking.
              </p>
            </div>
          ) : (
            <div className="border border-zinc-800 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-muted-foreground border-b border-zinc-800 bg-zinc-900/50">
                    <th className="text-left py-2 px-3">Score</th>
                    <th className="text-left py-2 px-3">Verdict</th>
                    <th className="text-left py-2 px-3 hidden sm:table-cell">Source</th>
                    <th className="text-left py-2 px-3 hidden md:table-cell">Platform</th>
                    <th className="text-left py-2 px-3 hidden lg:table-cell">Feedback</th>
                    <th className="text-left py-2 px-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {reviews.map((review) => {
                    const verdictStyle = VERDICT_STYLES[review.verdict] || VERDICT_STYLES.pending;
                    return (
                      <tr
                        key={review.id}
                        onClick={() => loadReviewDetail(review.id)}
                        className="border-b border-zinc-800/50 last:border-0 hover:bg-zinc-800/30 cursor-pointer transition"
                      >
                        <td className="py-2 px-3">
                          <ScoreBadge score={review.overall_score} />
                        </td>
                        <td className="py-2 px-3">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${verdictStyle.bg} ${verdictStyle.color}`}>
                            {verdictStyle.label}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-xs text-muted-foreground hidden sm:table-cell">
                          {review.content_ref_type}
                        </td>
                        <td className="py-2 px-3 text-xs text-muted-foreground hidden md:table-cell">
                          {review.platform || "—"}
                        </td>
                        <td className="py-2 px-3 text-xs text-muted-foreground hidden lg:table-cell max-w-xs truncate">
                          {review.feedback || "—"}
                        </td>
                        <td className="py-2 px-3 text-xs text-muted-foreground">
                          {new Date(review.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Detail Panel */}
          {selectedReview && (
            <ReviewDetail
              review={selectedReview}
              onClose={() => setSelectedReview(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}
