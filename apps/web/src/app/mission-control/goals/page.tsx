"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { goalsApi, AgentGoal, GoalCreate } from "@/lib/api/goals";
import { MC_SUB_NAV } from "../constants";

const GOAL_TYPES = [
  { value: "posting_frequency", label: "Posting Frequency", desc: "e.g., Post 3x/week on LinkedIn", icon: "📅" },
  { value: "engagement_growth", label: "Engagement Growth", desc: "e.g., Grow engagement by 20%", icon: "📈" },
  { value: "research_cadence", label: "Research Cadence", desc: "e.g., Research 2 competitors/month", icon: "🔍" },
  { value: "content_pipeline", label: "Content Pipeline", desc: "e.g., Maintain 5 items in queue", icon: "📦" },
  { value: "custom", label: "Custom Goal", desc: "Any custom goal", icon: "🎯" },
];

const UNIT_LABELS: Record<string, string> = {
  per_week: "/ week",
  per_month: "/ month",
  percent: "%",
  count: "",
};

const STATUS_STYLES: Record<string, { bg: string; label: string }> = {
  active: { bg: "bg-green-500/20 text-green-400", label: "Active" },
  paused: { bg: "bg-yellow-500/20 text-yellow-400", label: "Paused" },
  completed: { bg: "bg-blue-500/20 text-blue-400", label: "Completed" },
  archived: { bg: "bg-zinc-500/20 text-zinc-400", label: "Archived" },
};

export default function GoalsPage() {
  const [goals, setGoals] = useState<AgentGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState<GoalCreate>({
    title: "",
    goal_type: "posting_frequency",
    target_value: 3,
    target_unit: "per_week",
  });

  const loadGoals = useCallback(async () => {
    try {
      const data = await goalsApi.list();
      setGoals(data);
    } catch (err) {
      console.error("Failed to load goals:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGoals();
  }, [loadGoals]);

  const handleCreate = async () => {
    if (!formData.title.trim()) return;
    try {
      await goalsApi.create(formData);
      setShowCreate(false);
      setFormData({ title: "", goal_type: "posting_frequency", target_value: 3, target_unit: "per_week" });
      loadGoals();
    } catch (err) {
      console.error("Failed to create goal:", err);
    }
  };

  const handleStatusChange = async (goalId: string, status: string) => {
    try {
      await goalsApi.update(goalId, { status } as Partial<AgentGoal>);
      loadGoals();
    } catch (err) {
      console.error("Failed to update goal:", err);
    }
  };

  const handleDelete = async (goalId: string) => {
    try {
      await goalsApi.delete(goalId);
      loadGoals();
    } catch (err) {
      console.error("Failed to delete goal:", err);
    }
  };

  const handleEvaluate = async (goalId: string) => {
    try {
      await goalsApi.evaluate(goalId);
      loadGoals();
    } catch (err) {
      console.error("Failed to evaluate goal:", err);
    }
  };

  const activeGoals = goals.filter((g) => g.status === "active");
  const otherGoals = goals.filter((g) => g.status !== "active");

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Sub-navigation */}
      <div className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="flex items-center gap-1 px-5 py-2 overflow-x-auto">
          {MC_SUB_NAV.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition whitespace-nowrap ${
                link.href === "/mission-control/goals"
                  ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-5 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Agent Goals</h1>
            <p className="text-xs text-zinc-500 mt-1">
              Set goals for your agents to track and work toward autonomously
            </p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 text-black text-xs font-bold hover:bg-amber-400 transition"
          >
            + New Goal
          </button>
        </div>

        {/* Create form */}
        {showCreate && (
          <div className="mb-6 p-5 rounded-xl border border-zinc-800 bg-zinc-900">
            <h3 className="text-sm font-semibold text-zinc-200 mb-4">Create a New Goal</h3>

            <div className="space-y-4">
              <div>
                <label className="text-[10px] text-zinc-500 uppercase tracking-wider">Goal Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., Post 3x/week on LinkedIn"
                  className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] text-zinc-500 uppercase tracking-wider">Goal Type</label>
                  <select
                    value={formData.goal_type}
                    onChange={(e) => setFormData({ ...formData, goal_type: e.target.value })}
                    className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-zinc-600"
                  >
                    {GOAL_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.icon} {t.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[10px] text-zinc-500 uppercase tracking-wider">Target</label>
                  <div className="flex gap-2 mt-1">
                    <input
                      type="number"
                      value={formData.target_value}
                      onChange={(e) => setFormData({ ...formData, target_value: Number(e.target.value) })}
                      min={1}
                      className="w-20 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-zinc-600"
                    />
                    <select
                      value={formData.target_unit}
                      onChange={(e) => setFormData({ ...formData, target_unit: e.target.value })}
                      className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-zinc-600"
                    >
                      <option value="per_week">per week</option>
                      <option value="per_month">per month</option>
                      <option value="percent">percent</option>
                      <option value="count">count</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 rounded-lg bg-zinc-800 text-zinc-400 text-xs hover:bg-zinc-700 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={!formData.title.trim()}
                  className="px-4 py-2 rounded-lg bg-amber-500 text-black text-xs font-bold hover:bg-amber-400 disabled:opacity-40 transition"
                >
                  Create Goal
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <p className="text-xs text-zinc-600 text-center py-8">Loading goals...</p>
        ) : goals.length === 0 ? (
          <div className="text-center py-12">
            <span className="text-4xl">🎯</span>
            <h3 className="text-sm font-semibold text-zinc-300 mt-4">No goals yet</h3>
            <p className="text-xs text-zinc-500 mt-1">
              Set goals like &quot;Post 3x/week&quot; and your agents will track progress automatically
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Active Goals */}
            {activeGoals.length > 0 && (
              <div>
                <h2 className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3">
                  Active Goals ({activeGoals.length})
                </h2>
                <div className="space-y-3">
                  {activeGoals.map((goal) => (
                    <GoalCard
                      key={goal.id}
                      goal={goal}
                      onStatusChange={handleStatusChange}
                      onDelete={handleDelete}
                      onEvaluate={handleEvaluate}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Other Goals */}
            {otherGoals.length > 0 && (
              <div>
                <h2 className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3">
                  Other Goals ({otherGoals.length})
                </h2>
                <div className="space-y-3">
                  {otherGoals.map((goal) => (
                    <GoalCard
                      key={goal.id}
                      goal={goal}
                      onStatusChange={handleStatusChange}
                      onDelete={handleDelete}
                      onEvaluate={handleEvaluate}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function GoalCard({
  goal,
  onStatusChange,
  onDelete,
  onEvaluate,
}: {
  goal: AgentGoal;
  onStatusChange: (id: string, status: string) => void;
  onDelete: (id: string) => void;
  onEvaluate: (id: string) => void;
}) {
  const pct = goal.target_value > 0 ? Math.min(100, (goal.current_value / goal.target_value) * 100) : 0;
  const statusStyle = STATUS_STYLES[goal.status] || STATUS_STYLES.active;
  const typeInfo = GOAL_TYPES.find((t) => t.value === goal.goal_type);

  return (
    <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{typeInfo?.icon || "🎯"}</span>
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">{goal.title}</h3>
            {goal.description && (
              <p className="text-[11px] text-zinc-500 mt-0.5">{goal.description}</p>
            )}
          </div>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${statusStyle.bg}`}>
          {statusStyle.label}
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-zinc-500">
            {goal.current_value} / {goal.target_value} {UNIT_LABELS[goal.target_unit] || ""}
          </span>
          <span className={`text-[10px] font-bold ${pct >= 70 ? "text-green-400" : pct >= 40 ? "text-amber-400" : "text-red-400"}`}>
            {pct.toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Meta + actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {goal.last_evaluated_at && (
            <span className="text-[9px] text-zinc-600">
              Evaluated {new Date(goal.last_evaluated_at).toLocaleDateString()}
            </span>
          )}
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 font-medium">
            {goal.priority}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onEvaluate(goal.id)}
            className="px-2 py-1 rounded text-[10px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
            title="Evaluate now"
          >
            Eval
          </button>
          {goal.status === "active" ? (
            <button
              onClick={() => onStatusChange(goal.id, "paused")}
              className="px-2 py-1 rounded text-[10px] text-yellow-400 hover:bg-zinc-800 transition"
            >
              Pause
            </button>
          ) : goal.status === "paused" ? (
            <button
              onClick={() => onStatusChange(goal.id, "active")}
              className="px-2 py-1 rounded text-[10px] text-green-400 hover:bg-zinc-800 transition"
            >
              Resume
            </button>
          ) : null}
          <button
            onClick={() => onDelete(goal.id)}
            className="px-2 py-1 rounded text-[10px] text-red-400 hover:bg-zinc-800 transition"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
