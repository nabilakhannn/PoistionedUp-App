"use client";

/**
 * Content Kanban — Notion-style editable pipeline (Slice 90)
 * Slice 92d: Added visible error feedback instead of silent error swallowing
 *
 * Features:
 * - Shows pipeline stages as columns (Research → Writing → QA → Your Review → Published)
 * - [+ Add Stage] creates a new column
 * - Click stage title to rename inline
 * - Toggle each stage: Auto (agent) vs Manual (human)
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ContentStage, stagesApi } from "@/lib/api/stages";

const STAGE_COLORS: Record<string, { border: string; badge: string; dot: string }> = {
  blue: { border: "border-blue-500/30", badge: "bg-blue-500/10 text-blue-400", dot: "bg-blue-400" },
  purple: { border: "border-purple-500/30", badge: "bg-purple-500/10 text-purple-400", dot: "bg-purple-400" },
  amber: { border: "border-amber-500/30", badge: "bg-amber-500/10 text-amber-400", dot: "bg-amber-400" },
  orange: { border: "border-orange-500/30", badge: "bg-orange-500/10 text-orange-400", dot: "bg-orange-400" },
  green: { border: "border-green-500/30", badge: "bg-green-500/10 text-green-400", dot: "bg-green-400" },
  red: { border: "border-red-500/30", badge: "bg-red-500/10 text-red-400", dot: "bg-red-400" },
  zinc: { border: "border-zinc-500/30", badge: "bg-zinc-500/10 text-zinc-400", dot: "bg-zinc-400" },
};

const AVAILABLE_COLORS = ["blue", "purple", "amber", "orange", "green", "red", "zinc"] as const;

function StageColumn({
  stage,
  onRename,
  onDelete,
  onToggleType,
}: {
  stage: ContentStage;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
  onToggleType: (id: string, type: "auto" | "manual") => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(stage.name);
  const inputRef = useRef<HTMLInputElement>(null);

  const colors = STAGE_COLORS[stage.color] || STAGE_COLORS.blue;

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commitRename = () => {
    setEditing(false);
    const trimmed = draft.trim();
    if (trimmed && trimmed !== stage.name) {
      onRename(stage.id, trimmed);
    } else {
      setDraft(stage.name);
    }
  };

  return (
    <div className={`flex-shrink-0 w-48 rounded-xl border ${colors.border} bg-card/40`}>
      {/* Column header */}
      <div className="px-3 py-2.5 border-b border-border/50">
        <div className="flex items-center gap-2 mb-1">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
          {editing ? (
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitRename();
                if (e.key === "Escape") { setEditing(false); setDraft(stage.name); }
              }}
              className="flex-1 min-w-0 bg-transparent text-sm font-semibold text-foreground outline-none border-b border-primary"
            />
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="flex-1 min-w-0 text-left text-sm font-semibold text-foreground hover:text-primary transition truncate"
              title="Click to rename"
            >
              {stage.name}
            </button>
          )}
        </div>

        {/* Auto / Manual toggle */}
        <button
          onClick={() => onToggleType(stage.id, stage.stage_type === "auto" ? "manual" : "auto")}
          className={`text-[10px] px-2 py-0.5 rounded-full ${colors.badge} hover:opacity-80 transition`}
          title={stage.stage_type === "auto" ? "Agent-handled (click for manual)" : "Manual review (click for auto)"}
        >
          {stage.stage_type === "auto" ? "🤖 Auto" : "👤 Manual"}
        </button>

        {/* Agent label */}
        {stage.stage_type === "auto" && stage.agent_id && (
          <div className="text-[9px] text-muted-foreground/60 mt-0.5 truncate">
            {stage.agent_id}
          </div>
        )}
      </div>

      {/* Empty state */}
      <div className="px-3 py-3 min-h-[80px] text-center">
        <div className="text-[10px] text-muted-foreground/40 mt-4">No items</div>
      </div>

      {/* Delete button (only non-default stages) */}
      {!stage.is_default && (
        <div className="px-3 py-2 border-t border-border/50">
          <button
            onClick={() => onDelete(stage.id)}
            className="w-full text-[10px] text-muted-foreground/50 hover:text-red-400 transition"
          >
            Remove stage
          </button>
        </div>
      )}
    </div>
  );
}

interface ContentKanbanProps {
  brandId: string;
}

export function ContentKanban({ brandId }: ContentKanbanProps) {
  const [stages, setStages] = useState<ContentStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [newStageName, setNewStageName] = useState("");
  const [newStageColor, setNewStageColor] = useState<string>("blue");

  const loadStages = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await stagesApi.list(brandId);
      setStages(data);
    } catch {
      setLoadError("Could not load stages. Check your connection and try refreshing.");
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    loadStages();
  }, [loadStages]);

  const clearActionError = () => setActionError(null);

  const handleRename = async (id: string, name: string) => {
    clearActionError();
    try {
      const updated = await stagesApi.update(id, { name });
      setStages((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch {
      setActionError("Rename failed — the stage name was not saved. Please try again.");
      // Revert: loadStages to restore original name
      loadStages();
    }
  };

  const handleDelete = async (id: string) => {
    clearActionError();
    // Optimistic remove
    setStages((prev) => prev.filter((s) => s.id !== id));
    try {
      await stagesApi.delete(id);
    } catch {
      setActionError("Could not remove the stage. Please try again.");
      loadStages(); // Restore
    }
  };

  const handleToggleType = async (id: string, type: "auto" | "manual") => {
    clearActionError();
    // Optimistic update
    setStages((prev) => prev.map((s) => (s.id === id ? { ...s, stage_type: type } : s)));
    try {
      const updated = await stagesApi.update(id, { stage_type: type });
      setStages((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch {
      setActionError("Could not update stage type. Please try again.");
      loadStages(); // Restore
    }
  };

  const handleAddStage = async () => {
    const name = newStageName.trim();
    if (!name) return;
    clearActionError();
    try {
      const created = await stagesApi.create({
        brand_id: brandId,
        name,
        color: newStageColor,
        stage_type: "manual",
      });
      setStages((prev) => [...prev, created]);
      setNewStageName("");
      setAdding(false);
    } catch {
      setActionError("Could not create stage. Please check your connection and try again.");
    }
  };

  if (loading) {
    return (
      <div className="flex gap-3 overflow-x-auto pb-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex-shrink-0 w-48 h-32 rounded-xl border border-border/30 bg-card/20 animate-pulse" />
        ))}
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/5 px-5 py-4 flex items-center gap-3">
        <span className="text-lg">⚠️</span>
        <div className="flex-1">
          <p className="text-sm font-medium text-foreground">Failed to load Kanban</p>
          <p className="text-xs text-muted-foreground mt-0.5">{loadError}</p>
        </div>
        <button
          onClick={loadStages}
          className="text-xs text-primary hover:underline shrink-0"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Action error banner */}
      {actionError && (
        <div className="flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-2.5">
          <span className="text-sm">⚠️</span>
          <p className="flex-1 text-xs text-foreground">{actionError}</p>
          <button
            onClick={clearActionError}
            className="text-xs text-muted-foreground hover:text-foreground shrink-0"
          >
            ✕
          </button>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={() => { setAdding(true); clearActionError(); }}
          className="text-xs text-muted-foreground hover:text-foreground border border-border rounded-lg px-3 py-1.5 hover:border-primary/50 transition"
        >
          + Add Stage
        </button>
      </div>

      {/* Add stage form */}
      {adding && (
        <div className="flex items-center gap-2 p-3 rounded-xl border border-primary/30 bg-primary/5">
          <input
            autoFocus
            value={newStageName}
            onChange={(e) => setNewStageName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAddStage();
              if (e.key === "Escape") { setAdding(false); setNewStageName(""); }
            }}
            placeholder="Stage name..."
            className="flex-1 bg-transparent text-sm outline-none text-foreground placeholder-muted-foreground"
          />
          <div className="flex items-center gap-1">
            {AVAILABLE_COLORS.map((c) => (
              <button
                key={c}
                onClick={() => setNewStageColor(c)}
                className={`w-4 h-4 rounded-full border-2 transition ${
                  newStageColor === c ? "border-white scale-110" : "border-transparent opacity-60"
                } ${STAGE_COLORS[c]?.dot || "bg-blue-400"}`}
              />
            ))}
          </div>
          <button
            onClick={handleAddStage}
            className="text-xs bg-primary text-primary-foreground px-3 py-1 rounded-lg"
          >
            Add
          </button>
          <button
            onClick={() => { setAdding(false); setNewStageName(""); }}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Kanban columns */}
      <div className="flex gap-3 overflow-x-auto pb-4">
        {stages.map((stage) => (
          <StageColumn
            key={stage.id}
            stage={stage}
            onRename={handleRename}
            onDelete={handleDelete}
            onToggleType={handleToggleType}
          />
        ))}
      </div>
    </div>
  );
}
