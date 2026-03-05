"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { brandApi } from "../../../lib/api";

export default function FoundationPage() {
  const [data, setData] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    brandApi
      .getProfile()
      .then((p) => setData(p.foundation || {}))
      .catch((e) => setError(e.message));
  }, []);

  const update = (path: string, value: any) => {
    const parts = path.split(".");
    const next = { ...data };
    let current: any = next;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]] || typeof current[parts[i]] !== "object") {
        current[parts[i]] = {};
      }
      current[parts[i]] = { ...current[parts[i]] };
      current = current[parts[i]];
    }
    current[parts[parts.length - 1]] = value;
    setData(next);
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await brandApi.updateFoundation(data);
      setSaved(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const suggest = async (field: string) => {
    try {
      const res = await brandApi.suggest(field, { foundation: data });
      update(field.replace("foundation.", ""), res.suggestion);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const itFactor = data.it_factor || {};

  return (
    <main className="max-w-3xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/brand" className="text-sm text-primary hover:underline">
            Back to Brand
          </Link>
          <h1 className="text-2xl font-bold mt-1">Foundation</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Who are you? What makes you different? This is where your brand starts.
          </p>
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="px-5 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition"
        >
          {saving ? "Saving..." : saved ? "Saved" : "Save"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Market Beliefs */}
      <Section title="Your Non-Negotiable Beliefs">
        <p className="text-sm text-muted-foreground mb-3">
          What do you believe about your market that most people get wrong?
          Strong opinions attract the right people and repel the wrong ones.
          List 3-5 beliefs.
        </p>
        <ListField
          items={(data.beliefs || []) as string[]}
          onChange={(v) => update("beliefs", v)}
          placeholder="e.g. Most LinkedIn advice is recycled garbage that doesn't work for B2B"
        />
      </Section>

      {/* IT Factor */}
      <Section title="Your IT Factor (Unfair Advantage)">
        <TextArea
          label="What is your unfair advantage?"
          value={itFactor.unfair_advantage || ""}
          onChange={(v) => update("it_factor.unfair_advantage", v)}
          onSuggest={() => suggest("foundation.it_factor.unfair_advantage")}
          hint="Something from your life, background, or experience nobody else can claim. e.g. 'I lost 20kg and now know what it takes mentally and physically to get there.'"
        />
        <TextArea
          label="How can you use it to build your personal brand?"
          value={itFactor.leverage_for_brand || ""}
          onChange={(v) => update("it_factor.leverage_for_brand", v)}
          onSuggest={() => suggest("foundation.it_factor.leverage_for_brand")}
          hint="e.g. 'Storytell about my transformation. Makes me relatable.'"
        />
        <TextArea
          label="How does it connect to your niche?"
          value={itFactor.leverage_for_niche || ""}
          onChange={(v) => update("it_factor.leverage_for_niche", v)}
          onSuggest={() => suggest("foundation.it_factor.leverage_for_niche")}
          hint="e.g. 'I'm in AI B2B SaaS, I understand psychology and compounding — I can build systems around what makes people happy.'"
        />
        <TextArea
          label="How does it help with selling and converting?"
          value={itFactor.leverage_for_selling || ""}
          onChange={(v) => update("it_factor.leverage_for_selling", v)}
          hint="e.g. 'People in my situation can relate to me, I can talk about how fitness x business made me a great person.'"
        />
        <TextArea
          label="How does it help build a bigger network?"
          value={itFactor.leverage_for_network || ""}
          onChange={(v) => update("it_factor.leverage_for_network", v)}
          hint="e.g. 'My content connects me with thousands of new people and gives me a distinctive in.'"
        />
      </Section>

      {/* Professional Achievements */}
      <Section title="Professional Achievements">
        <p className="text-sm text-muted-foreground mb-3">
          Social proof and authority builders. List as many as you can: client
          results, revenue milestones, certifications, media features, viral
          posts, etc.
        </p>
        <ListField
          items={(data.achievements_professional || []) as string[]}
          onChange={(v) => update("achievements_professional", v)}
          placeholder="e.g. Helped a client increase revenue by $50K in six weeks"
        />
      </Section>

      {/* Personal Achievements */}
      <Section title="Personal Achievements &amp; Backstory">
        <p className="text-sm text-muted-foreground mb-3">
          What makes people relate to you as a human, not just a business owner?
          Failures, turning points, beliefs, personal milestones.
        </p>
        <ListField
          items={(data.achievements_personal || []) as string[]}
          onChange={(v) => update("achievements_personal", v)}
          placeholder="e.g. I grew up in a council house until I was 15"
        />
      </Section>

      {/* Macro Story */}
      <Section title="Your Macro Story">
        <p className="text-sm text-muted-foreground mb-3">
          The big story of your career journey. How did you get from where you
          started to where you are now? This is the highlight reel people will
          remember.
        </p>
        <TextArea
          label="Your career journey"
          value={data.macro_story || ""}
          onChange={(v) => update("macro_story", v)}
          onSuggest={() => suggest("foundation.macro_story")}
        />
      </Section>

      {/* Micro Stories */}
      <Section title="Micro Stories">
        <p className="text-sm text-muted-foreground mb-3">
          Small, everyday moments that show what you&apos;re about. A
          conversation with a client, a lesson learned last week, a random
          Tuesday realization. These fuel your content.
        </p>
        <ListField
          items={(data.micro_stories || []) as string[]}
          onChange={(v) => update("micro_stories", v)}
          placeholder="e.g. Yesterday a client said 'I wish I started this 6 months ago' and it hit different"
        />
      </Section>

      {/* Content Pillars */}
      <Section title="Content Pillars">
        <p className="text-sm text-muted-foreground mb-3">
          3-5 topics you&apos;ll consistently post about. These should overlap
          what you know, what you love, and what your market needs.
        </p>
        <Field
          label="Content pillars (comma-separated)"
          value={(data.content_pillars || []).join(", ")}
          onChange={(v) =>
            update(
              "content_pillars",
              v
                .split(",")
                .map((s: string) => s.trim())
                .filter(Boolean)
            )
          }
          onSuggest={() => suggest("foundation.content_pillars")}
        />
      </Section>

      <div className="mt-8 flex justify-end">
        <button
          onClick={save}
          disabled={saving}
          className="px-5 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </main>
  );
}

/* ── Reusable components ────────────────────────────────── */

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-border">
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  onSuggest,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  onSuggest?: () => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-sm font-medium text-muted-foreground">{label}</label>
        {onSuggest && (
          <button
            onClick={onSuggest}
            className="text-xs text-primary hover:underline"
          >
            AI Suggest
          </button>
        )}
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
      />
    </div>
  );
}

function TextArea({
  label,
  value,
  onChange,
  onSuggest,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  onSuggest?: () => void;
  hint?: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-sm font-medium text-muted-foreground">{label}</label>
        {onSuggest && (
          <button
            onClick={onSuggest}
            className="text-xs text-primary hover:underline"
          >
            AI Suggest
          </button>
        )}
      </div>
      {hint && <p className="text-xs text-muted-foreground mb-1">{hint}</p>}
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className="w-full border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
      />
    </div>
  );
}

function ListField({
  items,
  onChange,
  placeholder,
}: {
  items: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");

  const add = () => {
    const trimmed = draft.trim();
    if (trimmed) {
      onChange([...items, trimmed]);
      setDraft("");
    }
  };

  const remove = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      add();
    }
  };

  return (
    <div>
      {items.length > 0 && (
        <ul className="space-y-2 mb-3">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-2 bg-card border border-border rounded-lg px-3 py-2 text-sm"
            >
              <span className="flex-1">{item}</span>
              <button
                onClick={() => remove(i)}
                className="text-muted-foreground hover:text-red-500 text-xs mt-0.5"
              >
                remove
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="flex-1 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
        />
        <button
          onClick={add}
          disabled={!draft.trim()}
          className="px-3 py-2 bg-muted text-muted-foreground rounded-lg text-sm font-medium hover:bg-accent disabled:opacity-50 transition"
        >
          Add
        </button>
      </div>
    </div>
  );
}
