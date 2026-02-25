"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  userTrainingApi,
  type CustomInstructions,
} from "@/lib/api/training";

interface CustomInstructionsPanelProps {
  brandId: string;
}

export function CustomInstructionsPanel({
  brandId,
}: CustomInstructionsPanelProps) {
  const [instructions, setInstructions] = useState<CustomInstructions | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Edit form state
  const [text, setText] = useState("");
  const [tone, setTone] = useState("");
  const [avoidTopics, setAvoidTopics] = useState("");
  const [focusAreas, setFocusAreas] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await userTrainingApi.getInstructions(brandId);
      setInstructions(data);
      if (data) {
        setText(data.instructions || "");
        setTone(data.tone_preference || "");
        setAvoidTopics((data.avoid_topics || []).join(", "));
        setFocusAreas((data.focus_areas || []).join(", "));
      }
    } catch (e) {
      console.error("Failed to load instructions:", e);
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    try {
      setSaving(true);
      const saved = await userTrainingApi.saveInstructions(brandId, {
        instructions: text,
        tone_preference: tone || undefined,
        avoid_topics: avoidTopics
          ? avoidTopics.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        focus_areas: focusAreas
          ? focusAreas.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
      });
      setInstructions(saved);
      setEditing(false);
    } catch (e) {
      console.error("Failed to save instructions:", e);
    } finally {
      setSaving(false);
    }
  };

  const hasInstructions =
    instructions &&
    (instructions.instructions ||
      instructions.tone_preference ||
      (instructions.avoid_topics && instructions.avoid_topics.length > 0) ||
      (instructions.focus_areas && instructions.focus_areas.length > 0));

  return (
    <div className="border-t border-zinc-800 pt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs">⚙️</span>
          <span className="text-xs font-medium text-zinc-400">
            Custom Instructions
          </span>
          {hasInstructions && (
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          )}
        </div>
        <svg
          className={`w-3.5 h-3.5 text-zinc-500 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {loading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-3 w-full bg-zinc-800 rounded" />
              <div className="h-3 w-2/3 bg-zinc-800 rounded" />
            </div>
          ) : editing ? (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-zinc-500 block mb-1">
                  Instructions for the AI
                </label>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="e.g. Always reference my book 'The Brand Blueprint'. Use my catchphrase 'Level up or lose out'."
                  className="w-full h-20 bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg p-2 text-xs resize-y focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-500 block mb-1">
                  Preferred Tone
                </label>
                <input
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  placeholder="e.g. bold, direct, no fluff"
                  className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-500 block mb-1">
                  Topics to Avoid (comma-separated)
                </label>
                <input
                  value={avoidTopics}
                  onChange={(e) => setAvoidTopics(e.target.value)}
                  placeholder="e.g. politics, religion"
                  className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-500 block mb-1">
                  Focus Areas (comma-separated)
                </label>
                <input
                  value={focusAreas}
                  onChange={(e) => setFocusAreas(e.target.value)}
                  placeholder="e.g. sales, conversion, coaching"
                  className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : hasInstructions ? (
            <div className="space-y-2">
              {instructions?.instructions && (
                <p className="text-xs text-zinc-300">
                  {instructions.instructions}
                </p>
              )}
              {instructions?.tone_preference && (
                <div className="flex items-center gap-1">
                  <span className="text-zinc-500 text-xs">Tone:</span>
                  <span className="text-xs text-zinc-300">
                    {instructions.tone_preference}
                  </span>
                </div>
              )}
              {instructions?.avoid_topics &&
                instructions.avoid_topics.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-zinc-500 text-xs">Avoid:</span>
                    {instructions.avoid_topics.map((t) => (
                      <span
                        key={t}
                        className="text-xs bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              {instructions?.focus_areas &&
                instructions.focus_areas.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-zinc-500 text-xs">Focus:</span>
                    {instructions.focus_areas.map((f) => (
                      <span
                        key={f}
                        className="text-xs bg-green-500/10 text-green-400 px-1.5 py-0.5 rounded"
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                )}
              <button
                onClick={() => setEditing(true)}
                className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-2"
              >
                Edit
              </button>
            </div>
          ) : (
            <div className="text-center py-2">
              <p className="text-xs text-zinc-500 mb-2">
                Tell the AI how to coach you better
              </p>
              <button
                onClick={() => setEditing(true)}
                className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-2"
              >
                Add Instructions
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
