"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { brandApi } from "../../../lib/api";

export default function BrandStrategyPage() {
  const [brand, setBrand] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    brandApi
      .getProfile()
      .then((p) => setBrand(p.brand || {}))
      .catch((e) => setError(e.message));
  }, []);

  const update = (path: string, value: any) => {
    const parts = path.split(".");
    const next = { ...brand };
    let current: any = next;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]] || typeof current[parts[i]] !== "object") {
        current[parts[i]] = {};
      }
      current[parts[i]] = { ...current[parts[i]] };
      current = current[parts[i]];
    }
    current[parts[parts.length - 1]] = value;
    setBrand(next);
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await brandApi.updateStatement(brand);
      setSaved(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const suggest = async (field: string) => {
    try {
      const res = await brandApi.suggest(field, { brand });
      update(field.replace("brand.", ""), res.suggestion);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const itFactor = brand.it_factor || {};

  return (
    <main className="max-w-3xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/brand" className="text-sm text-blue-600 hover:underline">
            Back to Brand
          </Link>
          <h1 className="text-2xl font-bold mt-1">Brand Strategy</h1>
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {saving ? "Saving..." : saved ? "Saved" : "Save"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Brand Statement */}
      <Section title="Brand Statement">
        <p className="text-sm text-gray-500 mb-3">
          Formula: We help (Ideal Client) achieve (Tangible Result) and
          (Emotional Benefit) by (How).
        </p>
        <TextArea
          label="Your brand statement"
          value={brand.statement || ""}
          onChange={(v) => update("statement", v)}
          onSuggest={() => suggest("brand.statement")}
        />
      </Section>

      {/* IT Factor */}
      <Section title="Your IT Factor (Unfair Advantage)">
        <TextArea
          label="What is your unfair advantage?"
          value={itFactor.unfair_advantage || ""}
          onChange={(v) => update("it_factor.unfair_advantage", v)}
          onSuggest={() => suggest("brand.it_factor.unfair_advantage")}
          hint="Something from your life, background, or experience nobody else can claim."
        />
        <TextArea
          label="How can you use it to build your personal brand?"
          value={itFactor.leverage_for_brand || ""}
          onChange={(v) => update("it_factor.leverage_for_brand", v)}
          onSuggest={() => suggest("brand.it_factor.leverage_for_brand")}
        />
        <TextArea
          label="How does it connect to your niche?"
          value={itFactor.leverage_for_niche || ""}
          onChange={(v) => update("it_factor.leverage_for_niche", v)}
          onSuggest={() => suggest("brand.it_factor.leverage_for_niche")}
        />
        <TextArea
          label="How does it help with selling and converting?"
          value={itFactor.leverage_for_selling || ""}
          onChange={(v) => update("it_factor.leverage_for_selling", v)}
        />
        <TextArea
          label="How does it help build a bigger network?"
          value={itFactor.leverage_for_network || ""}
          onChange={(v) => update("it_factor.leverage_for_network", v)}
        />
      </Section>

      {/* Content Pillars */}
      <Section title="Content Pillars">
        <p className="text-sm text-gray-500 mb-3">
          3-5 topics you will consistently talk about. These define what you are
          known for.
        </p>
        <Field
          label="Content pillars (comma-separated)"
          value={(brand.content_pillars || []).join(", ")}
          onChange={(v) =>
            update(
              "content_pillars",
              v
                .split(",")
                .map((s: string) => s.trim())
                .filter(Boolean)
            )
          }
          onSuggest={() => suggest("brand.content_pillars")}
        />
      </Section>

      <div className="mt-8 flex justify-end">
        <button
          onClick={save}
          disabled={saving}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-gray-200">{title}</h2>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Field({ label, value, onChange, onSuggest }: { label: string; value: string; onChange: (v: string) => void; onSuggest?: () => void }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        {onSuggest && <button onClick={onSuggest} className="text-xs text-blue-600 hover:underline">AI Suggest</button>}
      </div>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
    </div>
  );
}

function TextArea({ label, value, onChange, onSuggest, hint }: { label: string; value: string; onChange: (v: string) => void; onSuggest?: () => void; hint?: string }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        {onSuggest && <button onClick={onSuggest} className="text-xs text-blue-600 hover:underline">AI Suggest</button>}
      </div>
      {hint && <p className="text-xs text-gray-400 mb-1">{hint}</p>}
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
    </div>
  );
}
