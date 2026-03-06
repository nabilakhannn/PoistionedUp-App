"use client";

import { useState } from "react";
import { campaignsApi, type CampaignCreate } from "@/lib/api/campaigns";

const TEMPLATES = [
  { id: "30-day-linkedin", name: "30-Day LinkedIn Authority", pieces: 30, platforms: ["linkedin"], description: "Daily LinkedIn posts for 30 days" },
  { id: "launch-week", name: "Launch Week Blitz", pieces: 14, platforms: ["linkedin", "twitter"], description: "2 posts/day across platforms for 7 days" },
  { id: "pillar-dive", name: "Content Pillar Deep Dive", pieces: 15, platforms: ["linkedin"], description: "5 posts per pillar, 3 pillars" },
  { id: "custom", name: "Custom Campaign", pieces: 5, platforms: ["linkedin"], description: "Define everything yourself" },
];

const PLATFORM_OPTIONS = ["linkedin", "twitter", "instagram", "facebook", "newsletter"];

interface CampaignCreatorProps {
  brandId: string;
  onCreated?: () => void;
  onCancel?: () => void;
}

export function CampaignCreator({ brandId, onCreated, onCancel }: CampaignCreatorProps) {
  const [step, setStep] = useState<"template" | "details">("template");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["linkedin"]);
  const [totalPieces, setTotalPieces] = useState(5);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId);
    const t = TEMPLATES.find((tpl) => tpl.id === templateId);
    if (t) {
      if (templateId !== "custom") setName(t.name);
      setTotalPieces(t.pieces);
      setPlatforms(t.platforms);
    }
    setStep("details");
  };

  const togglePlatform = (p: string) => {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  };

  const handleCreate = async () => {
    if (!name.trim()) { setError("Name is required"); return; }
    if (platforms.length === 0) { setError("Select at least one platform"); return; }

    setSaving(true);
    setError(null);
    try {
      const data: CampaignCreate = {
        brand_id: brandId,
        name: name.trim(),
        description: description.trim(),
        platforms,
        total_pieces: totalPieces,
        template_id: selectedTemplate ?? undefined,
      };
      await campaignsApi.create(data);
      onCreated?.();
    } catch {
      setError("Failed to create campaign");
    } finally {
      setSaving(false);
    }
  };

  if (step === "template") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-200">Choose a template</h3>
          {onCancel && (
            <button onClick={onCancel} className="text-xs text-zinc-500 hover:text-zinc-300">Cancel</button>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.id}
              onClick={() => handleTemplateSelect(t.id)}
              className="glass-card text-left hover:bg-white/[0.06] transition-colors"
            >
              <p className="text-sm font-medium text-zinc-200">{t.name}</p>
              <p className="text-xs text-zinc-500 mt-1">{t.description}</p>
              <p className="text-[10px] text-zinc-600 mt-2">{t.pieces} pieces · {t.platforms.join(", ")}</p>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-200">Campaign Details</h3>
        <button onClick={() => setStep("template")} className="text-xs text-zinc-500 hover:text-zinc-300">← Back</button>
      </div>

      <div>
        <label className="text-xs text-zinc-500 block mb-1">Campaign Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Q1 LinkedIn Authority"
          className="glass-input w-full"
        />
      </div>

      <div>
        <label className="text-xs text-zinc-500 block mb-1">Description (optional)</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What's the goal of this campaign?"
          rows={2}
          className="glass-input w-full resize-none"
        />
      </div>

      <div>
        <label className="text-xs text-zinc-500 block mb-1">Platforms</label>
        <div className="flex flex-wrap gap-1.5">
          {PLATFORM_OPTIONS.map((p) => (
            <button
              key={p}
              onClick={() => togglePlatform(p)}
              className={`text-xs px-2.5 py-1 rounded-full transition-colors capitalize ${
                platforms.includes(p)
                  ? "bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/25"
                  : "text-zinc-500 bg-white/[0.03] ring-1 ring-white/[0.05]"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-zinc-500 block mb-1">Total Pieces</label>
        <input
          type="number"
          value={totalPieces}
          onChange={(e) => setTotalPieces(Math.max(1, Math.min(100, parseInt(e.target.value) || 1)))}
          className="glass-input w-24"
          min={1}
          max={100}
        />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="flex items-center gap-3">
        <button onClick={handleCreate} disabled={saving} className="glass-button-primary text-sm">
          {saving ? "Creating..." : "Create Campaign"}
        </button>
        {onCancel && (
          <button onClick={onCancel} className="glass-button text-sm">Cancel</button>
        )}
      </div>
    </div>
  );
}
