"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  experimentsApi,
  voiceApi,
  ExperimentSummary,
  SelfVoiceDNA,
  VoiceDriftResult,
} from "../../lib/api";

const STATUS_COLORS: Record<string, string> = {
  proposed: "bg-yellow-100 text-yellow-800",
  approved: "bg-blue-100 text-blue-800",
  running: "bg-indigo-100 text-indigo-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-gray-100 text-gray-500",
};

const WINNER_LABELS: Record<string, string> = {
  variant_a: "Variant A won",
  variant_b: "Variant B won",
  inconclusive: "Inconclusive",
};

const PLATFORMS = ["youtube", "linkedin", "instagram", "twitter", "tiktok"];
const VARIABLES = ["hook_type", "topic_category", "cta_style", "posting_time", "content_structure"];

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"experiments" | "voice" | "create">("experiments");

  // Create form
  const [newHypothesis, setNewHypothesis] = useState("");
  const [newVariable, setNewVariable] = useState("hook_type");
  const [newVariantA, setNewVariantA] = useState("");
  const [newVariantB, setNewVariantB] = useState("");
  const [newPlatform, setNewPlatform] = useState("youtube");
  const [newTargetPosts, setNewTargetPosts] = useState(4);

  // Voice state
  const [voiceDna, setVoiceDna] = useState<SelfVoiceDNA | null>(null);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [driftText, setDriftText] = useState("");
  const [driftResult, setDriftResult] = useState<VoiceDriftResult | null>(null);
  const [driftChecking, setDriftChecking] = useState(false);

  async function loadExperiments() {
    try {
      setLoading(true);
      setError("");
      const data = await experimentsApi.list();
      setExperiments(data);
    } catch (err: any) {
      setError(err.message || "Failed to load experiments");
    } finally {
      setLoading(false);
    }
  }

  async function loadVoice() {
    try {
      const data = await voiceApi.getBaseline();
      setVoiceDna(data);
    } catch {
      // No baseline yet — that's fine
    }
  }

  useEffect(() => {
    loadExperiments();
    loadVoice();
  }, []);

  async function handleApprove(id: string) {
    try {
      await experimentsApi.approve(id);
      loadExperiments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleCancel(id: string) {
    try {
      await experimentsApi.cancel(id);
      loadExperiments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleConclude(id: string) {
    try {
      await experimentsApi.conclude(id);
      loadExperiments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this experiment permanently?")) return;
    try {
      await experimentsApi.delete(id);
      loadExperiments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleAutoPropose() {
    try {
      setError("");
      const proposed = await experimentsApi.autoPropose();
      if (proposed.length === 0) {
        setError("No experiments to propose yet. Need at least 5 logged posts with engagement data.");
      }
      loadExperiments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newHypothesis.trim() || !newVariantA.trim() || !newVariantB.trim()) return;
    try {
      await experimentsApi.create({
        hypothesis: newHypothesis,
        variable: newVariable,
        variant_a: newVariantA,
        variant_b: newVariantB,
        platform: newPlatform,
        target_posts: newTargetPosts,
      });
      setNewHypothesis("");
      setNewVariantA("");
      setNewVariantB("");
      setTab("experiments");
      loadExperiments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleAnalyzeVoice() {
    try {
      setVoiceLoading(true);
      setError("");
      const result = await voiceApi.analyzeSelf();
      setVoiceDna(result.voice_dna);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setVoiceLoading(false);
    }
  }

  async function handleDriftCheck() {
    if (!driftText.trim()) return;
    try {
      setDriftChecking(true);
      setDriftResult(null);
      const result = await voiceApi.checkDrift(driftText);
      setDriftResult(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDriftChecking(false);
    }
  }

  const proposed = experiments.filter((e) => e.status === "proposed");
  const active = experiments.filter((e) => e.status === "approved" || e.status === "running");
  const completed = experiments.filter((e) => e.status === "completed" || e.status === "cancelled");

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            &larr; Home
          </Link>
          <h1 className="text-2xl font-bold mt-1">Experiments & Voice</h1>
          <p className="text-sm text-gray-500 mt-1">
            A/B test content strategies and maintain your authentic voice
          </p>
        </div>
        <button
          onClick={handleAutoPropose}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
        >
          Auto-Propose Experiments
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b">
        {[
          { key: "experiments" as const, label: `Experiments (${experiments.length})` },
          { key: "voice" as const, label: "Voice DNA & Drift" },
          { key: "create" as const, label: "New Experiment" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === t.key
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── EXPERIMENTS TAB ───────────────────────────── */}
      {tab === "experiments" && (
        <>
          {loading ? (
            <p className="text-gray-400 text-center py-8">Loading experiments...</p>
          ) : experiments.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-lg mb-2">No experiments yet</p>
              <p className="text-sm">
                Create an experiment manually or click &quot;Auto-Propose&quot; to let the agent
                suggest experiments based on your performance data.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Proposed */}
              {proposed.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-yellow-800 mb-3">
                    Proposed ({proposed.length})
                  </h2>
                  <div className="space-y-3">
                    {proposed.map((exp) => (
                      <div key={exp.id} className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[exp.status]}`}>
                            {exp.status}
                          </span>
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                            {exp.platform}
                          </span>
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                            {exp.variable}
                          </span>
                        </div>
                        <p className="text-sm text-gray-900 mb-2">{exp.hypothesis}</p>
                        <p className="text-xs text-gray-500 mb-3">
                          Testing: &quot;{exp.variant_a}&quot; vs &quot;{exp.variant_b}&quot;
                          ({exp.target_posts} posts per variant)
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleApprove(exp.id)}
                            className="px-4 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleDelete(exp.id)}
                            className="px-4 py-1.5 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Active */}
              {active.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-indigo-800 mb-3">
                    Active ({active.length})
                  </h2>
                  <div className="space-y-3">
                    {active.map((exp) => (
                      <div key={exp.id} className="p-4 bg-white rounded-lg border shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[exp.status]}`}>
                            {exp.status}
                          </span>
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                            {exp.platform}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-gray-900 mb-2">{exp.hypothesis}</p>
                        <div className="grid grid-cols-2 gap-4 mb-3">
                          <div className="p-3 bg-blue-50 rounded-lg">
                            <p className="text-xs font-medium text-blue-800">Variant A: {exp.variant_a}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <div className="flex-1 bg-blue-200 rounded-full h-2">
                                <div
                                  className="bg-blue-600 h-2 rounded-full"
                                  style={{ width: `${Math.min(100, (exp.variant_a_count / exp.target_posts) * 100)}%` }}
                                />
                              </div>
                              <span className="text-xs text-blue-700">{exp.variant_a_count}/{exp.target_posts}</span>
                            </div>
                          </div>
                          <div className="p-3 bg-purple-50 rounded-lg">
                            <p className="text-xs font-medium text-purple-800">Variant B: {exp.variant_b}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <div className="flex-1 bg-purple-200 rounded-full h-2">
                                <div
                                  className="bg-purple-600 h-2 rounded-full"
                                  style={{ width: `${Math.min(100, (exp.variant_b_count / exp.target_posts) * 100)}%` }}
                                />
                              </div>
                              <span className="text-xs text-purple-700">{exp.variant_b_count}/{exp.target_posts}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          {exp.variant_a_count >= 2 && exp.variant_b_count >= 2 && (
                            <button
                              onClick={() => handleConclude(exp.id)}
                              className="px-4 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                            >
                              Conclude
                            </button>
                          )}
                          <button
                            onClick={() => handleCancel(exp.id)}
                            className="px-4 py-1.5 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Completed */}
              {completed.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-gray-600 mb-3">
                    Completed ({completed.length})
                  </h2>
                  <div className="space-y-3">
                    {completed.map((exp) => (
                      <div key={exp.id} className="p-4 bg-white rounded-lg border shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[exp.status]}`}>
                            {exp.status}
                          </span>
                          {exp.winner && (
                            <span className={`px-2 py-0.5 text-xs rounded-full ${
                              exp.winner === "inconclusive" ? "bg-gray-100 text-gray-600" : "bg-green-100 text-green-800"
                            }`}>
                              {WINNER_LABELS[exp.winner] || exp.winner}
                            </span>
                          )}
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                            {exp.platform}
                          </span>
                        </div>
                        <p className="text-sm text-gray-900 mb-1">{exp.hypothesis}</p>
                        {exp.conclusion && (
                          <p className="text-sm text-gray-600 mb-2">{exp.conclusion}</p>
                        )}
                        <div className="flex items-center gap-4 text-xs text-gray-400">
                          <span>A: {exp.variant_a} ({exp.variant_a_count} posts{exp.variant_a_avg_engagement != null ? `, ${(exp.variant_a_avg_engagement * 100).toFixed(2)}%` : ""})</span>
                          <span>B: {exp.variant_b} ({exp.variant_b_count} posts{exp.variant_b_avg_engagement != null ? `, ${(exp.variant_b_avg_engagement * 100).toFixed(2)}%` : ""})</span>
                        </div>
                        <button
                          onClick={() => handleDelete(exp.id)}
                          className="mt-2 text-xs text-gray-400 hover:text-red-500"
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ── VOICE DNA TAB ─────────────────────────────── */}
      {tab === "voice" && (
        <div className="space-y-6">
          {/* Self-Voice DNA */}
          <div className="bg-white rounded-lg border shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Your Voice DNA</h2>
              <button
                onClick={handleAnalyzeVoice}
                disabled={voiceLoading}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm"
              >
                {voiceLoading ? "Analyzing..." : voiceDna ? "Re-Analyze Voice" : "Analyze My Voice"}
              </button>
            </div>

            {!voiceDna ? (
              <div className="text-center py-8 text-gray-400">
                <p className="text-lg mb-2">No voice profile yet</p>
                <p className="text-sm">
                  You need at least 10 published posts logged in the Performance section.
                  Click &quot;Analyze My Voice&quot; to extract your natural writing style.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-xs text-gray-400">
                  Based on {voiceDna.posts_analyzed} published posts
                </p>

                <div className="grid grid-cols-2 gap-4">
                  {voiceDna.tone && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Tone</p>
                      <p className="text-sm text-gray-900">{voiceDna.tone}</p>
                    </div>
                  )}
                  {voiceDna.sentence_style && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Sentence Style</p>
                      <p className="text-sm text-gray-900">{voiceDna.sentence_style}</p>
                    </div>
                  )}
                  {voiceDna.vocabulary_level && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Vocabulary</p>
                      <p className="text-sm text-gray-900">{voiceDna.vocabulary_level}</p>
                    </div>
                  )}
                  {voiceDna.content_structure && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Structure</p>
                      <p className="text-sm text-gray-900">{voiceDna.content_structure}</p>
                    </div>
                  )}
                </div>

                {voiceDna.hook_patterns.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Hook Patterns</p>
                    <div className="flex gap-1 flex-wrap">
                      {voiceDna.hook_patterns.map((p, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs bg-sky-100 text-sky-800 rounded-full">{p}</span>
                      ))}
                    </div>
                  </div>
                )}

                {voiceDna.signature_phrases.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Signature Phrases</p>
                    <div className="flex gap-1 flex-wrap">
                      {voiceDna.signature_phrases.map((p, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs bg-amber-100 text-amber-800 rounded-full">&quot;{p}&quot;</span>
                      ))}
                    </div>
                  </div>
                )}

                {voiceDna.personality_traits.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Personality Traits</p>
                    <div className="flex gap-1 flex-wrap">
                      {voiceDna.personality_traits.map((p, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs bg-violet-100 text-violet-800 rounded-full">{p}</span>
                      ))}
                    </div>
                  </div>
                )}

                {voiceDna.sample_hooks.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Your Best Hooks</p>
                    <ul className="text-sm text-gray-700 space-y-1">
                      {voiceDna.sample_hooks.map((h, i) => (
                        <li key={i} className="pl-3 border-l-2 border-indigo-300">{h}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Drift Check */}
          <div className="bg-white rounded-lg border shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-2">Voice Drift Check</h2>
            <p className="text-sm text-gray-500 mb-4">
              Paste AI-generated content below to check if it matches your natural voice.
            </p>
            <textarea
              value={driftText}
              onChange={(e) => setDriftText(e.target.value)}
              rows={5}
              placeholder="Paste AI-generated text here..."
              className="w-full border rounded-lg px-3 py-2 text-sm mb-3"
            />
            <button
              onClick={handleDriftCheck}
              disabled={driftChecking || !driftText.trim() || !voiceDna}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm"
            >
              {driftChecking ? "Checking..." : "Check Drift"}
            </button>
            {!voiceDna && (
              <p className="text-xs text-gray-400 mt-2">
                Analyze your voice first before checking drift.
              </p>
            )}

            {driftResult && (
              <div className={`mt-4 p-4 rounded-lg ${
                driftResult.drift_level === "low" ? "bg-green-50" :
                driftResult.drift_level === "medium" ? "bg-yellow-50" : "bg-red-50"
              }`}>
                <div className="flex items-center gap-3 mb-3">
                  <span className={`text-2xl font-bold ${
                    driftResult.drift_level === "low" ? "text-green-700" :
                    driftResult.drift_level === "medium" ? "text-yellow-700" : "text-red-700"
                  }`}>
                    {Math.round(driftResult.drift_score * 100)}%
                  </span>
                  <div>
                    <p className={`text-sm font-medium ${
                      driftResult.drift_level === "low" ? "text-green-800" :
                      driftResult.drift_level === "medium" ? "text-yellow-800" : "text-red-800"
                    }`}>
                      {driftResult.drift_level === "low" ? "Low Drift - Good match!" :
                       driftResult.drift_level === "medium" ? "Medium Drift - Some differences" :
                       "High Drift - Significant divergence"}
                    </p>
                    <p className="text-xs text-gray-500">0% = perfect match, 100% = completely different</p>
                  </div>
                </div>

                {driftResult.details.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-medium text-gray-600 mb-1">Observations:</p>
                    <ul className="text-sm text-gray-700 space-y-1">
                      {driftResult.details.map((d, i) => (
                        <li key={i}>- {d}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {driftResult.recommendation && (
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-1">Recommendation:</p>
                    <p className="text-sm text-gray-700">{driftResult.recommendation}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── CREATE EXPERIMENT TAB ─────────────────────── */}
      {tab === "create" && (
        <form onSubmit={handleCreate} className="bg-white p-6 rounded-lg border shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Create an Experiment</h2>
          <p className="text-sm text-gray-500">
            Define an A/B test for your content. What do you want to test?
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hypothesis</label>
            <input
              type="text"
              value={newHypothesis}
              onChange={(e) => setNewHypothesis(e.target.value)}
              placeholder='e.g., "Story hooks outperform question hooks on YouTube"'
              className="w-full border rounded-lg px-3 py-2 text-sm"
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Variable</label>
              <select
                value={newVariable}
                onChange={(e) => setNewVariable(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                {VARIABLES.map((v) => (
                  <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Variant A</label>
              <input
                type="text"
                value={newVariantA}
                onChange={(e) => setNewVariantA(e.target.value)}
                placeholder='e.g., "story"'
                className="w-full border rounded-lg px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Variant B</label>
              <input
                type="text"
                value={newVariantB}
                onChange={(e) => setNewVariantB(e.target.value)}
                placeholder='e.g., "question"'
                className="w-full border rounded-lg px-3 py-2 text-sm"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
              <select
                value={newPlatform}
                onChange={(e) => setNewPlatform(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Posts per variant ({newTargetPosts})
              </label>
              <input
                type="range"
                min={2}
                max={10}
                value={newTargetPosts}
                onChange={(e) => setNewTargetPosts(parseInt(e.target.value))}
                className="w-full mt-2"
              />
            </div>
          </div>

          <button
            type="submit"
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
          >
            Create Experiment
          </button>
        </form>
      )}
    </main>
  );
}
