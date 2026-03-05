"use client";

import { TopicCandidate } from "../types";

interface TopicSelectionProps {
  topics: TopicCandidate[];
  onSelect: (id: string) => void;
  loading: boolean;
}

export function TopicSelection({ topics, onSelect, loading }: TopicSelectionProps) {
  if (topics.length === 0) {
    return (
      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-6 text-center">
        <h3 className="text-lg font-medium text-yellow-400 mb-1">Waiting for topics</h3>
        <p className="text-zinc-400 text-sm">
          The pipeline is generating topic candidates. This page will update when they are ready.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-bold text-white mb-1">Pick a Topic</h2>
      <p className="text-zinc-400 text-sm mb-4">
        The AI found {topics.length} topic candidates. Pick the one you want to create content about.
      </p>
      <div className="space-y-3">
        {topics.map((topic) => (
          <div
            key={topic.id}
            className="bg-zinc-900 border border-zinc-700/50 rounded-xl p-5 hover:border-blue-500/50 transition cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-medium text-white flex-1 pr-4">{topic.title}</h3>
              <span className="bg-blue-500/20 text-blue-400 text-xs font-medium px-2 py-0.5 rounded-lg">
                Score: {topic.opportunity_score}
              </span>
            </div>
            <p className="text-sm text-zinc-300 mb-2">{topic.audience_pain}</p>
            {topic.why_now && (
              <p className="text-sm text-zinc-500 mb-2">Why now: {topic.why_now}</p>
            )}
            {topic.risk_flags.length > 0 && (
              <div className="flex gap-1 mb-3 flex-wrap">
                {topic.risk_flags.map((flag, i) => (
                  <span key={i} className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-lg">
                    {flag}
                  </span>
                ))}
              </div>
            )}
            <button
              onClick={() => onSelect(topic.id)}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition disabled:opacity-50"
            >
              {loading ? "Selecting..." : "Select this topic"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
