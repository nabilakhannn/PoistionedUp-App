"use client";

import {
  QAReviewResult,
  SCORE_DIMENSIONS,
  VERDICT_STYLES,
} from "@/lib/api/qa";
import { ScoreBadge } from "./score-badge";

interface ReviewDetailProps {
  review: QAReviewResult;
  onClose?: () => void;
}

export function ReviewDetail({ review, onClose }: ReviewDetailProps) {
  const verdictStyle = VERDICT_STYLES[review.verdict] || VERDICT_STYLES.pending;

  return (
    <div className="border border-zinc-800 rounded-lg p-5 bg-zinc-900/30 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ScoreBadge score={review.overall_score} size="md" />
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${verdictStyle.bg} ${verdictStyle.color}`}>
            {verdictStyle.label}
          </span>
          {review.revision_number > 0 && (
            <span className="text-xs text-muted-foreground">
              Revision #{review.revision_number}
            </span>
          )}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Close
          </button>
        )}
      </div>

      {/* Score breakdown */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-muted-foreground">Score Breakdown</h4>
        {SCORE_DIMENSIONS.map((dim) => {
          const value = review.scores[dim.key];
          return (
            <div key={dim.key} className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-28 shrink-0">
                {dim.label} ({dim.weight})
              </span>
              <div className="flex-1 bg-zinc-800 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    value >= 80
                      ? "bg-green-500"
                      : value >= 50
                        ? "bg-yellow-500"
                        : "bg-red-500"
                  }`}
                  style={{ width: `${value}%` }}
                />
              </div>
              <span className="text-xs font-medium w-8 text-right">{value}</span>
            </div>
          );
        })}
      </div>

      {/* Feedback */}
      {review.feedback && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-1">Feedback</h4>
          <p className="text-sm text-foreground">{review.feedback}</p>
        </div>
      )}

      {/* Issues */}
      {review.issues.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">
            Issues ({review.issues.length})
          </h4>
          <div className="space-y-1">
            {review.issues.map((issue, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span
                  className={`px-1.5 py-0.5 rounded shrink-0 ${
                    issue.severity === "critical"
                      ? "bg-red-500/20 text-red-400"
                      : issue.severity === "warning"
                        ? "bg-yellow-500/20 text-yellow-400"
                        : "bg-zinc-500/20 text-zinc-400"
                  }`}
                >
                  {issue.severity}
                </span>
                <span className="text-muted-foreground">{issue.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk flags */}
      {review.risk_flags.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">
            Risk Flags ({review.risk_flags.length})
          </h4>
          <div className="space-y-1">
            {review.risk_flags.map((flag, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 shrink-0">
                  {flag.type}
                </span>
                <span className="text-muted-foreground">{flag.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Revision triggered */}
      {review.revision_triggered && (
        <div className="text-xs text-yellow-400 bg-yellow-500/10 px-3 py-2 rounded">
          Auto-revision triggered — content sent to Copywriter for improvement.
        </div>
      )}

      {/* Timestamp */}
      <div className="text-[10px] text-muted-foreground">
        Reviewed {new Date(review.created_at).toLocaleString()}
      </div>
    </div>
  );
}
