"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { brandApi } from "../../../lib/api";

export default function ICAFormPage() {
  const [ica, setIca] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    brandApi
      .getProfile()
      .then((p) => setIca(p.ica || {}))
      .catch((e) => setError(e.message));
  }, []);

  const update = (path: string, value: any) => {
    const parts = path.split(".");
    const next = { ...ica };
    let current: any = next;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]] || typeof current[parts[i]] !== "object") {
        current[parts[i]] = {};
      }
      current[parts[i]] = { ...current[parts[i]] };
      current = current[parts[i]];
    }
    current[parts[parts.length - 1]] = value;
    setIca(next);
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await brandApi.updateICA(ica);
      setSaved(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const suggest = async (field: string) => {
    try {
      const res = await brandApi.suggest(field, { ica });
      update(field.replace("ica.", ""), res.suggestion);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const demo = ica.demographics || {};
  const motivations = ica.buying_motivations || {};
  const fears = ica.purchase_fears || {};

  return (
    <main className="max-w-3xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            href="/brand"
            className="text-sm text-primary hover:underline"
          >
            Back to Brand
          </Link>
          <h1 className="text-2xl font-bold mt-1">Ideal Client Avatar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Define the ONE person you serve best. The deeper you go, the better
            your content will resonate.
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

      {/* Demographics */}
      <Section title="Demographics">
        <Field
          label="Name (give your avatar a real name)"
          value={demo.name || ""}
          onChange={(v) => update("demographics.name", v)}
          onSuggest={() => suggest("ica.demographics.name")}
        />
        <div className="grid grid-cols-2 gap-4">
          <Field
            label="Age"
            value={demo.age || ""}
            onChange={(v) => update("demographics.age", v)}
          />
          <Field
            label="Gender"
            value={demo.gender || ""}
            onChange={(v) => update("demographics.gender", v)}
          />
        </div>
        <Field
          label="Occupation / Job Title"
          value={demo.occupation || ""}
          onChange={(v) => update("demographics.occupation", v)}
          onSuggest={() => suggest("ica.demographics.occupation")}
        />
        <div className="grid grid-cols-2 gap-4">
          <Field
            label="Income range"
            value={demo.income || ""}
            onChange={(v) => update("demographics.income", v)}
          />
          <Field
            label="Location"
            value={demo.location || ""}
            onChange={(v) => update("demographics.location", v)}
          />
        </div>
        <Field
          label="Interests (comma-separated)"
          value={(demo.interests || []).join(", ")}
          onChange={(v) =>
            update(
              "demographics.interests",
              v.split(",").map((s: string) => s.trim()).filter(Boolean)
            )
          }
        />
      </Section>

      {/* Persona & Client Fit */}
      <Section title="Persona & Client Fit">
        <Field
          label="4 words that describe your ideal buyer (comma-separated)"
          value={(ica.persona_words || []).join(", ")}
          onChange={(v) =>
            update(
              "persona_words",
              v.split(",").map((s: string) => s.trim()).filter(Boolean)
            )
          }
          onSuggest={() => suggest("ica.persona_words")}
        />
        <ListField
          items={(ica.attract_clients || []) as string[]}
          onChange={(v) => update("attract_clients", v)}
          label="Clients you WANT to attract"
          placeholder="e.g. Ambitious founders who take action and respect boundaries"
        />
        <ListField
          items={(ica.red_flag_clients || []) as string[]}
          onChange={(v) => update("red_flag_clients", v)}
          label="Red-flag clients you want to AVOID"
          placeholder="e.g. People who want results without doing the work"
        />
      </Section>

      {/* 4 Buying Motivations */}
      <Section title="4 Buying Motivations">
        <p className="text-sm text-muted-foreground mb-3">
          There are 4 reasons people buy. Describe how EACH one shows up for
          your ideal client.
        </p>
        <TextArea
          label="Money — How do they want to make/save money?"
          value={motivations.money || ""}
          onChange={(v) => update("buying_motivations.money", v)}
          onSuggest={() => suggest("ica.buying_motivations.money")}
          hint="e.g. 'Wants to add $10K MRR but doesn't know how to attract premium clients'"
        />
        <TextArea
          label="Time — How does time pressure show up?"
          value={motivations.time || ""}
          onChange={(v) => update("buying_motivations.time", v)}
          onSuggest={() => suggest("ica.buying_motivations.time")}
          hint="e.g. 'Spends 3 hours/day on content that gets zero traction'"
        />
        <TextArea
          label="Performance — What skills or results are they chasing?"
          value={motivations.performance || ""}
          onChange={(v) => update("buying_motivations.performance", v)}
          onSuggest={() => suggest("ica.buying_motivations.performance")}
          hint="e.g. 'Wants to become a recognized thought leader in their space'"
        />
        <TextArea
          label="Perception — How do they want to be seen?"
          value={motivations.perception || ""}
          onChange={(v) => update("buying_motivations.perception", v)}
          onSuggest={() => suggest("ica.buying_motivations.perception")}
          hint="e.g. 'Wants to be known as THE go-to expert, not just another consultant'"
        />
      </Section>

      {/* Deep Discovery */}
      <Section title="Deep Discovery">
        <TextArea
          label="Their biggest NEED (the core problem)"
          value={ica.big_need || ""}
          onChange={(v) => update("big_need", v)}
          onSuggest={() => suggest("ica.big_need")}
        />
        <TextArea
          label="Their biggest WANT (dream outcome)"
          value={ica.big_want || ""}
          onChange={(v) => update("big_want", v)}
          onSuggest={() => suggest("ica.big_want")}
        />
        <TextArea
          label="What have they tried before? (and why it failed)"
          value={ica.tried_before || ""}
          onChange={(v) => update("tried_before", v)}
          onSuggest={() => suggest("ica.tried_before")}
        />
        <TextArea
          label="If they do nothing, what happens?"
          value={ica.if_nothing || ""}
          onChange={(v) => update("if_nothing", v)}
          onSuggest={() => suggest("ica.if_nothing")}
        />
      </Section>

      {/* Daily Frustrations & Dream Outcomes */}
      <Section title="Frustrations & Dreams">
        <ListField
          items={(ica.daily_frustrations || []) as string[]}
          onChange={(v) => update("daily_frustrations", v)}
          label="Daily frustrations (the daily grind that wears them down)"
          placeholder="e.g. Spends hours creating content that gets 3 likes"
        />
        <ListField
          items={(ica.dream_outcomes || []) as string[]}
          onChange={(v) => update("dream_outcomes", v)}
          label="Dream outcomes (if you could wave a magic wand)"
          placeholder="e.g. Wake up to inbound leads in their DMs every morning"
        />
      </Section>

      {/* Peskiest Problems & Biggest Fears */}
      <Section title="Problems & Fears (Go Deep)">
        <p className="text-sm text-muted-foreground mb-3">
          Push for 10 of each. The deeper you go, the better your content hooks.
        </p>
        <ListField
          items={(ica.peskiest_problems || []) as string[]}
          onChange={(v) => update("peskiest_problems", v)}
          label="Top 10 peskiest problems"
          placeholder="e.g. Can't get consistent leads from LinkedIn"
        />
        <ListField
          items={(ica.biggest_fears || []) as string[]}
          onChange={(v) => update("biggest_fears", v)}
          label="Top 10 biggest fears"
          placeholder="e.g. Being seen as just another coach in a saturated market"
        />
      </Section>

      {/* Self-Image vs Perception */}
      <Section title="Identity Gap">
        <TextArea
          label="How do they see themselves?"
          value={ica.self_image || ""}
          onChange={(v) => update("self_image", v)}
          onSuggest={() => suggest("ica.self_image")}
          hint="Their internal identity — what they believe about themselves"
        />
        <TextArea
          label="How does the world see them?"
          value={ica.external_perception || ""}
          onChange={(v) => update("external_perception", v)}
          onSuggest={() => suggest("ica.external_perception")}
          hint="The gap between self-image and external perception fuels your messaging"
        />
      </Section>

      {/* Purchase Barriers */}
      <Section title="Feelings Preventing Purchase">
        <TextArea
          label="Anxiety — What are they worried about?"
          value={fears.anxiety || ""}
          onChange={(v) => update("purchase_fears.anxiety", v)}
          onSuggest={() => suggest("ica.purchase_fears.anxiety")}
        />
        <TextArea
          label="Habits — What switching costs hold them back?"
          value={fears.habits || ""}
          onChange={(v) => update("purchase_fears.habits", v)}
          onSuggest={() => suggest("ica.purchase_fears.habits")}
        />
        <TextArea
          label="Inertia — Why might they do nothing?"
          value={fears.inertia || ""}
          onChange={(v) => update("purchase_fears.inertia", v)}
        />
      </Section>

      {/* Discovery Links */}
      <Section title="Discovery Resources">
        <Field
          label="Sales call recording link (optional)"
          value={ica.sales_call_link || ""}
          onChange={(v) => update("sales_call_link", v)}
        />
        <Field
          label="Discovery questionnaire link (optional)"
          value={ica.discovery_questionnaire_link || ""}
          onChange={(v) => update("discovery_questionnaire_link", v)}
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

// ── Reusable form components ─────────────────────────────

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
  label,
  placeholder,
}: {
  items: string[];
  onChange: (v: string[]) => void;
  label: string;
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
      <label className="text-sm font-medium text-muted-foreground mb-1 block">
        {label}
      </label>
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
