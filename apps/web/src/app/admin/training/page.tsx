"use client";

import { useState, useEffect, useCallback } from "react";
import {
  adminTrainingApi,
  type PromptConfig,
  type TrainingExample,
  type FeedbackEntry,
  type TrainingStats,
} from "@/lib/api/training";

// ── Tab types ─────────────────────────────────────────────────────

type Tab = "prompts" | "examples" | "feedback" | "stats";

const TABS: { key: Tab; label: string }[] = [
  { key: "prompts", label: "Prompt Config" },
  { key: "examples", label: "Training Examples" },
  { key: "feedback", label: "User Feedback" },
  { key: "stats", label: "Stats" },
];

// ── Main Page ─────────────────────────────────────────────────────

export default function AdminTrainingPage() {
  const [activeTab, setActiveTab] = useState<Tab>("prompts");

  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-card-foreground">
            Agent Training Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure prompt sections, manage examples, and review user feedback
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-card rounded-lg p-1 w-fit">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-primary/20 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "prompts" && <PromptConfigTab />}
        {activeTab === "examples" && <TrainingExamplesTab />}
        {activeTab === "feedback" && <FeedbackTab />}
        {activeTab === "stats" && <StatsTab />}
      </div>
    </div>
  );
}

// ── Prompt Config Tab ─────────────────────────────────────────────

function PromptConfigTab() {
  const [configs, setConfigs] = useState<PromptConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  const loadConfigs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminTrainingApi.listConfigs();
      setConfigs(data);
    } catch (e) {
      console.error("Failed to load configs:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const startEditing = (cfg: PromptConfig) => {
    setEditingKey(cfg.config_key);
    setEditContent(cfg.content);
  };

  const cancelEditing = () => {
    setEditingKey(null);
    setEditContent("");
  };

  const saveConfig = async (configKey: string) => {
    try {
      setSaving(true);
      await adminTrainingApi.updateConfig(configKey, editContent);
      setEditingKey(null);
      setEditContent("");
      await loadConfigs();
    } catch (e) {
      console.error("Failed to save config:", e);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSkeleton />;

  // Group by config_type
  const grouped: Record<string, PromptConfig[]> = {};
  for (const cfg of configs) {
    const type = cfg.config_type;
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(cfg);
  }

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([type, items]) => (
        <div key={type}>
          <h3 className="text-lg font-semibold text-foreground mb-3 capitalize">
            {type} Configs
          </h3>
          <div className="space-y-3">
            {items.map((cfg) => (
              <div
                key={cfg.id}
                className="bg-card border border-border rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-foreground font-medium">
                      {cfg.config_key}
                    </span>
                    <span className="text-muted-foreground text-xs ml-2">
                      v{cfg.version}
                    </span>
                  </div>
                  {editingKey !== cfg.config_key && (
                    <button
                      onClick={() => startEditing(cfg)}
                      className="text-primary hover:text-primary/80 text-sm"
                    >
                      Edit
                    </button>
                  )}
                </div>

                {editingKey === cfg.config_key ? (
                  <div className="space-y-3">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full h-64 bg-accent border border-border rounded-lg p-3 text-foreground text-sm font-mono resize-y focus:outline-none focus:border-primary"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => saveConfig(cfg.config_key)}
                        disabled={saving}
                        className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm disabled:opacity-50"
                      >
                        {saving ? "Saving..." : "Save (New Version)"}
                      </button>
                      <button
                        onClick={cancelEditing}
                        className="px-4 py-2 bg-accent hover:bg-accent/80 text-foreground rounded-lg text-sm"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <pre className="text-muted-foreground text-sm whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {cfg.content.slice(0, 500)}
                    {cfg.content.length > 500 && "..."}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {configs.length === 0 && (
        <EmptyState
          title="No Prompt Configs"
          description="Apply migration 019 to seed default prompt configs."
        />
      )}
    </div>
  );
}

// ── Training Examples Tab ─────────────────────────────────────────

const CATEGORIES = [
  "good_response",
  "bad_response",
  "pushback",
  "field_question",
  "voice_example",
] as const;

function TrainingExamplesTab() {
  const [examples, setExamples] = useState<TrainingExample[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);

  // Create form
  const [newCategory, setNewCategory] = useState("good_response");
  const [newModule, setNewModule] = useState("");
  const [newField, setNewField] = useState("");
  const [newInput, setNewInput] = useState("");
  const [newResponse, setNewResponse] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [creating, setCreating] = useState(false);

  const loadExamples = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminTrainingApi.listExamples(
        filterCategory || undefined
      );
      setExamples(data);
    } catch (e) {
      console.error("Failed to load examples:", e);
    } finally {
      setLoading(false);
    }
  }, [filterCategory]);

  useEffect(() => {
    loadExamples();
  }, [loadExamples]);

  const handleCreate = async () => {
    try {
      setCreating(true);
      await adminTrainingApi.createExample({
        category: newCategory,
        module: newModule || undefined,
        field: newField || undefined,
        user_input: newInput,
        ideal_response: newResponse,
        context_notes: newNotes || undefined,
      });
      setShowCreate(false);
      setNewInput("");
      setNewResponse("");
      setNewNotes("");
      await loadExamples();
    } catch (e) {
      console.error("Failed to create example:", e);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this training example?")) return;
    try {
      await adminTrainingApi.deleteExample(id);
      await loadExamples();
    } catch (e) {
      console.error("Failed to delete example:", e);
    }
  };

  if (loading) return <LoadingSkeleton />;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="bg-accent border border-border text-foreground rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm"
        >
          {showCreate ? "Cancel" : "+ Add Example"}
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-card border border-border rounded-lg p-4 space-y-3">
          <h3 className="text-foreground font-medium">New Training Example</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-muted-foreground text-xs block mb-1">
                Category
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="w-full bg-accent border border-border text-foreground rounded px-2 py-1.5 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-muted-foreground text-xs block mb-1">
                Module (optional)
              </label>
              <input
                value={newModule}
                onChange={(e) => setNewModule(e.target.value)}
                placeholder="e.g. foundation"
                className="w-full bg-accent border border-border text-foreground rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-muted-foreground text-xs block mb-1">
                Field (optional)
              </label>
              <input
                value={newField}
                onChange={(e) => setNewField(e.target.value)}
                placeholder="e.g. what_you_do"
                className="w-full bg-accent border border-border text-foreground rounded px-2 py-1.5 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="text-muted-foreground text-xs block mb-1">
              User Input
            </label>
            <textarea
              value={newInput}
              onChange={(e) => setNewInput(e.target.value)}
              placeholder="What the user says..."
              className="w-full h-20 bg-accent border border-border text-foreground rounded p-2 text-sm resize-y"
            />
          </div>
          <div>
            <label className="text-muted-foreground text-xs block mb-1">
              Ideal Response
            </label>
            <textarea
              value={newResponse}
              onChange={(e) => setNewResponse(e.target.value)}
              placeholder="How the agent should respond..."
              className="w-full h-24 bg-accent border border-border text-foreground rounded p-2 text-sm resize-y"
            />
          </div>
          <div>
            <label className="text-muted-foreground text-xs block mb-1">
              Context Notes
            </label>
            <input
              value={newNotes}
              onChange={(e) => setNewNotes(e.target.value)}
              placeholder="Why this is a good/bad example"
              className="w-full bg-accent border border-border text-foreground rounded px-2 py-1.5 text-sm"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !newInput || !newResponse}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create Example"}
          </button>
        </div>
      )}

      {/* Examples List */}
      <div className="space-y-3">
        {examples.map((ex) => (
          <div
            key={ex.id}
            className="bg-card border border-border rounded-lg p-4"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    ex.category === "good_response"
                      ? "bg-green-500/20 text-green-400"
                      : ex.category === "bad_response"
                      ? "bg-red-500/20 text-red-400"
                      : ex.category === "pushback"
                      ? "bg-amber-500/20 text-amber-400"
                      : "bg-primary/20 text-primary"
                  }`}
                >
                  {ex.category.replace(/_/g, " ")}
                </span>
                {ex.module && (
                  <span className="text-xs bg-accent text-muted-foreground px-2 py-0.5 rounded">
                    {ex.module}
                    {ex.field && `.${ex.field}`}
                  </span>
                )}
              </div>
              <button
                onClick={() => handleDelete(ex.id)}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                Delete
              </button>
            </div>
            <div className="space-y-2">
              <div>
                <span className="text-muted-foreground text-xs">User:</span>
                <p className="text-foreground text-sm">{ex.user_input}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-xs">Ideal:</span>
                <p className="text-foreground text-sm">{ex.ideal_response}</p>
              </div>
              {ex.context_notes && (
                <div>
                  <span className="text-muted-foreground text-xs">Why:</span>
                  <p className="text-muted-foreground text-sm italic">
                    {ex.context_notes}
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {examples.length === 0 && !showCreate && (
        <EmptyState
          title="No Training Examples"
          description="Add examples to teach the agent how to respond better."
          action={() => setShowCreate(true)}
          actionLabel="Add First Example"
        />
      )}
    </div>
  );
}

// ── Feedback Tab ──────────────────────────────────────────────────

function FeedbackTab() {
  const [feedback, setFeedback] = useState<FeedbackEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("");

  const loadFeedback = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminTrainingApi.listFeedback(
        filterType || undefined,
        50
      );
      setFeedback(data);
    } catch (e) {
      console.error("Failed to load feedback:", e);
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    loadFeedback();
  }, [loadFeedback]);

  if (loading) return <LoadingSkeleton />;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-2">
        {["", "thumbs_up", "thumbs_down", "correction", "voice_mismatch"].map(
          (type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                filterType === type
                  ? "bg-primary/20 text-primary"
                  : "bg-accent text-muted-foreground hover:bg-accent/80"
              }`}
            >
              {type
                ? type === "thumbs_up"
                  ? "👍 Up"
                  : type === "thumbs_down"
                  ? "👎 Down"
                  : type === "correction"
                  ? "✏️ Corrections"
                  : "🔊 Voice"
                : "All"}
            </button>
          )
        )}
      </div>

      {/* Feedback List */}
      <div className="space-y-3">
        {feedback.map((fb) => (
          <div
            key={fb.id}
            className="bg-card border border-border rounded-lg p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">
                {fb.feedback_type === "thumbs_up"
                  ? "👍"
                  : fb.feedback_type === "thumbs_down"
                  ? "👎"
                  : fb.feedback_type === "correction"
                  ? "✏️"
                  : "🔊"}
              </span>
              <span className="text-muted-foreground text-xs">
                {fb.created_at
                  ? new Date(fb.created_at).toLocaleDateString()
                  : ""}
              </span>
              <span className="text-muted-foreground text-xs">
                User: {fb.user_id?.slice(0, 8)}...
              </span>
            </div>
            {fb.feedback_text && (
              <p className="text-foreground text-sm mb-2">{fb.feedback_text}</p>
            )}
            {fb.original_response && (
              <div className="bg-accent rounded p-2 mt-2">
                <span className="text-muted-foreground text-xs block mb-1">
                  Original response:
                </span>
                <p className="text-muted-foreground text-xs">
                  {fb.original_response.slice(0, 300)}
                  {fb.original_response.length > 300 && "..."}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {feedback.length === 0 && (
        <EmptyState
          title="No Feedback Yet"
          description="User feedback will appear here when users interact with the strategist."
        />
      )}
    </div>
  );
}

// ── Stats Tab ─────────────────────────────────────────────────────

function StatsTab() {
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await adminTrainingApi.getStats();
        setStats(data);
      } catch (e) {
        console.error("Failed to load stats:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <LoadingSkeleton />;
  if (!stats) return <EmptyState title="Could not load stats" description="" />;

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Prompt Configs" value={stats.total_configs} />
        <StatCard label="Training Examples" value={stats.total_examples} />
        <StatCard label="Total Feedback" value={stats.total_feedback} />
      </div>

      {/* Feedback Breakdown */}
      {Object.keys(stats.feedback_by_type).length > 0 && (
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-foreground font-medium mb-3">
            Feedback Breakdown
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(stats.feedback_by_type).map(([type, count]) => (
              <div key={type} className="bg-accent rounded-lg p-3 text-center">
                <div className="text-2xl mb-1">
                  {type === "thumbs_up"
                    ? "👍"
                    : type === "thumbs_down"
                    ? "👎"
                    : type === "correction"
                    ? "✏️"
                    : "🔊"}
                </div>
                <div className="text-foreground font-bold">{count}</div>
                <div className="text-muted-foreground text-xs">
                  {type.replace(/_/g, " ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Corrections */}
      {stats.recent_corrections.length > 0 && (
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-foreground font-medium mb-3">
            Recent Corrections
          </h3>
          <div className="space-y-2">
            {stats.recent_corrections.map((fb) => (
              <div
                key={fb.id}
                className="bg-accent rounded p-3 text-sm text-foreground"
              >
                {fb.feedback_text || "(no text)"}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Shared Components ─────────────────────────────────────────────

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 text-center">
      <div className="text-3xl font-bold text-card-foreground">{value}</div>
      <div className="text-muted-foreground text-sm mt-1">{label}</div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-card border border-border rounded-lg p-4 animate-pulse"
        >
          <div className="h-4 bg-accent rounded w-1/3 mb-3" />
          <div className="h-3 bg-accent rounded w-full mb-2" />
          <div className="h-3 bg-accent rounded w-2/3" />
        </div>
      ))}
    </div>
  );
}

function EmptyState({
  title,
  description,
  action,
  actionLabel,
}: {
  title: string;
  description: string;
  action?: () => void;
  actionLabel?: string;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-8 text-center">
      <h3 className="text-foreground font-medium text-lg">{title}</h3>
      <p className="text-muted-foreground mt-2">{description}</p>
      {action && actionLabel && (
        <button
          onClick={action}
          className="mt-4 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
