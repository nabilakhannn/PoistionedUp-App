"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { brandApi } from "../../../lib/api";

const OFFER_TYPES = [
  {
    value: "timed",
    label: "Timed",
    desc: "Specific deadline: 'In 90 days you'll have X'",
  },
  {
    value: "transformation",
    label: "Transformation",
    desc: "Journey-based: 'Go from A to B'",
  },
  {
    value: "logical",
    label: "Logical",
    desc: "Feature-based: 'You get X, Y, Z'",
  },
];

export default function OfferFormPage() {
  const [offer, setOffer] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    brandApi
      .getProfile()
      .then((p) => setOffer(p.offer || {}))
      .catch((e) => setError(e.message));
  }, []);

  const update = (path: string, value: any) => {
    const parts = path.split(".");
    const next = { ...offer };
    let current: any = next;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]] || typeof current[parts[i]] !== "object") {
        current[parts[i]] = {};
      }
      current[parts[i]] = { ...current[parts[i]] };
      current = current[parts[i]];
    }
    current[parts[parts.length - 1]] = value;
    setOffer(next);
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await brandApi.updateOffer(offer);
      setSaved(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const suggest = async (field: string) => {
    try {
      const res = await brandApi.suggest(field, { offer });
      update(field.replace("offer.", ""), res.suggestion);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const magic = offer.magic || {};
  const measurable = magic.measurable || {};
  const actionable = magic.actionable || {};
  const generous = magic.generous || {};
  const scalable = magic.scalable || {};
  const clear = magic.clear || {};
  const valueEq = offer.value_equation || {};
  const market = offer.market || {};
  const framework = offer.framework || {};
  const boosters = offer.boosters || {};
  const grandSlam = offer.grand_slam || {};
  const enhancers = grandSlam.enhancers || {};

  return (
    <main className="max-w-3xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/brand" className="text-sm text-primary hover:underline">
            Back to Brand
          </Link>
          <h1 className="text-2xl font-bold mt-1">Your Offer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Build an irresistible offer using the MAGIC Offer Framework +
            Hormozi&apos;s $100M Grand Slam Offer. Each section makes your
            offer stronger.
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

      {/* Core Offer Summary */}
      <Section title="Core Offer">
        <TextArea
          label="What is your offer? (Describe it like you would to a friend)"
          value={offer.what || ""}
          onChange={(v) => update("what", v)}
          onSuggest={() => suggest("offer.what")}
        />
        <div className="grid grid-cols-2 gap-4">
          <Field
            label="Price & structure"
            value={offer.price || ""}
            onChange={(v) => update("price", v)}
          />
          <Field
            label="Target audience"
            value={offer.target_audience || ""}
            onChange={(v) => update("target_audience", v)}
            onSuggest={() => suggest("offer.target_audience")}
          />
        </div>
      </Section>

      {/* Offer Type */}
      <Section title="Offer Type">
        <p className="text-sm text-muted-foreground mb-3">
          Which type best describes your offer?
        </p>
        <div className="grid grid-cols-3 gap-3">
          {OFFER_TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => update("offer_type", t.value)}
              className={`p-3 rounded-lg border text-left text-sm transition ${
                offer.offer_type === t.value
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-border bg-card text-muted-foreground hover:border-border"
              }`}
            >
              <div className="font-medium">{t.label}</div>
              <div className="text-xs text-muted-foreground mt-1">{t.desc}</div>
            </button>
          ))}
        </div>
      </Section>

      {/* M - Measurable */}
      <MagicSection letter="M" title="Measurable" color="blue">
        <TextArea
          label="What specific, quantifiable outcome can your clients expect?"
          value={measurable.quantifiable_outcome || ""}
          onChange={(v) => update("magic.measurable.quantifiable_outcome", v)}
          onSuggest={() => suggest("offer.magic.measurable.quantifiable_outcome")}
          hint="Not 'grow your business' but 'add $10K MRR in 90 days'"
        />
        <ListField
          items={(measurable.milestones || []) as string[]}
          onChange={(v) => update("magic.measurable.milestones", v)}
          label="Key milestones along the way (3-5 checkpoints)"
          placeholder="e.g. Week 2: Brand foundation complete + first 3 posts live"
        />
        <Field
          label="How long until they see first results?"
          value={measurable.time_to_first_results || ""}
          onChange={(v) => update("magic.measurable.time_to_first_results", v)}
        />
      </MagicSection>

      {/* A - Actionable */}
      <MagicSection letter="A" title="Actionable" color="green">
        <TextArea
          label="What is the FIRST thing someone does after they buy?"
          value={actionable.first_action || ""}
          onChange={(v) => update("magic.actionable.first_action", v)}
          hint="Eliminate the 'now what?' anxiety"
        />
        <ListField
          items={(actionable.process_steps || []) as string[]}
          onChange={(v) => update("magic.actionable.process_steps", v)}
          label="Exact steps in your process (the transformation journey)"
          placeholder="e.g. Step 1: 60-min brand discovery call to map your foundation"
        />
        <ListField
          items={(actionable.tools_and_resources || []) as string[]}
          onChange={(v) => update("magic.actionable.tools_and_resources", v)}
          label="Tools, templates, and resources they get"
          placeholder="e.g. Brand Strategy Document, Content Calendar Template"
        />
      </MagicSection>

      {/* G - Generous */}
      <MagicSection letter="G" title="Generous" color="yellow">
        <TextArea
          label="What would make someone feel STUPID for saying no?"
          value={generous.irresistible_reason || ""}
          onChange={(v) => update("magic.generous.irresistible_reason", v)}
          onSuggest={() => suggest("offer.magic.generous.irresistible_reason")}
          hint="Stack the value — make the offer a no-brainer"
        />
        <ListField
          items={(generous.bonuses || []) as string[]}
          onChange={(v) => update("magic.generous.bonuses", v)}
          label="Bonuses (high perceived value, low cost to you)"
          placeholder="e.g. Free hook library template ($500 value)"
        />
        <TextArea
          label="What guarantee eliminates all risk for the buyer?"
          value={generous.guarantee || ""}
          onChange={(v) => update("magic.generous.guarantee", v)}
          hint="30-day refund? Results guarantee? Something else?"
        />
      </MagicSection>

      {/* I - Infinitely Scalable */}
      <MagicSection letter="I" title="Infinitely Scalable" color="purple">
        <TextArea
          label="Can you deliver this without trading more of YOUR time?"
          value={scalable.delivery_model || ""}
          onChange={(v) => update("magic.scalable.delivery_model", v)}
          hint="1:1, group, course, hybrid? What's the delivery model?"
        />
        <ListField
          items={(scalable.systematized_parts || []) as string[]}
          onChange={(v) => update("magic.scalable.systematized_parts", v)}
          label="What parts can be systematized or automated?"
          placeholder="e.g. Onboarding sequence is fully automated via email"
        />
        <Field
          label="Maximum clients you can serve at this price point?"
          value={scalable.max_clients || ""}
          onChange={(v) => update("magic.scalable.max_clients", v)}
        />
      </MagicSection>

      {/* C - Clear */}
      <MagicSection letter="C" title="Clear" color="red">
        <TextArea
          label="Describe your offer in ONE sentence (elevator pitch test)"
          value={clear.one_sentence || ""}
          onChange={(v) => update("magic.clear.one_sentence", v)}
          onSuggest={() => suggest("offer.magic.clear.one_sentence")}
          hint="If someone can't understand it in one sentence, it's not clear enough"
        />
        <div className="grid grid-cols-2 gap-4">
          <TextArea
            label="BEFORE state of your client"
            value={clear.before_state || ""}
            onChange={(v) => update("magic.clear.before_state", v)}
            hint="Paint the picture of their current pain"
          />
          <TextArea
            label="AFTER state of your client"
            value={clear.after_state || ""}
            onChange={(v) => update("magic.clear.after_state", v)}
            hint="Paint the picture of their transformed life"
          />
        </div>
        <TextArea
          label="Why should they buy from YOU and not someone else?"
          value={clear.why_you || ""}
          onChange={(v) => update("magic.clear.why_you", v)}
          onSuggest={() => suggest("offer.magic.clear.why_you")}
        />
        <TextArea
          label="What's the cost of NOT buying? (Pain of inaction)"
          value={clear.cost_of_inaction || ""}
          onChange={(v) => update("magic.clear.cost_of_inaction", v)}
          onSuggest={() => suggest("offer.magic.clear.cost_of_inaction")}
        />
        <TextArea
          label="Social proof (testimonials, case studies, numbers)"
          value={clear.social_proof || ""}
          onChange={(v) => update("magic.clear.social_proof", v)}
        />
        <TextArea
          label="Why is the price worth 10x what you charge?"
          value={clear.price_justification || ""}
          onChange={(v) => update("magic.clear.price_justification", v)}
        />
        <Field
          label="Your irresistible CTA — what do they do RIGHT NOW?"
          value={clear.cta || ""}
          onChange={(v) => update("magic.clear.cta", v)}
        />
      </MagicSection>

      {/* Value Equation */}
      <Section title="Value Equation">
        <p className="text-sm text-muted-foreground mb-3">
          Value = (Dream Outcome x Perceived Likelihood) / (Time x Effort).
          Rate each factor for your offer.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <TextArea
            label="Dream Outcome — How big is the result?"
            value={valueEq.dream_outcome || ""}
            onChange={(v) => update("value_equation.dream_outcome", v)}
          />
          <TextArea
            label="Perceived Likelihood — How likely do they believe it'll work?"
            value={valueEq.perceived_likelihood || ""}
            onChange={(v) => update("value_equation.perceived_likelihood", v)}
          />
          <TextArea
            label="Time to Result — How fast?"
            value={valueEq.time_to_result || ""}
            onChange={(v) => update("value_equation.time_to_result", v)}
          />
          <TextArea
            label="Effort Required — How easy?"
            value={valueEq.effort_required || ""}
            onChange={(v) => update("value_equation.effort_required", v)}
          />
        </div>
      </Section>

      {/* Grand Slam Offer (Hormozi $100M Offers) */}
      <div className="mb-8 rounded-lg border-l-4 border-orange-500 bg-orange-50 p-5">
        <div className="flex items-center gap-3 mb-1">
          <span className="w-8 h-8 rounded-full flex items-center justify-center bg-orange-600 text-white font-bold text-sm">
            $
          </span>
          <h2 className="text-lg font-semibold">
            Grand Slam Offer
          </h2>
          <span className="text-xs bg-orange-200 text-orange-800 px-2 py-0.5 rounded-full font-medium">
            Hormozi $100M Offers
          </span>
        </div>
        <p className="text-xs text-orange-700 mb-4 ml-11">
          &quot;Make people an offer so good they would feel stupid saying no.&quot;
        </p>
        <div className="space-y-4">
          <TextArea
            label="Who is your 'starving crowd'?"
            value={grandSlam.starving_crowd || ""}
            onChange={(v) => update("grand_slam.starving_crowd", v)}
            hint="People so desperate for a solution they'll buy almost anything — massive pain + money to pay + easy to find"
          />
          <TextArea
            label="Dream outcome statement — the #1 result they want"
            value={grandSlam.dream_outcome_statement || ""}
            onChange={(v) => update("grand_slam.dream_outcome_statement", v)}
            onSuggest={() => suggest("offer.grand_slam.dream_outcome_statement")}
          />
          <ProblemSolutionList
            items={(grandSlam.problems_solutions || []) as Array<{problem: string; solution: string; delivery_vehicle?: string; sexy_name?: string}>}
            onChange={(v) => update("grand_slam.problems_solutions", v)}
          />
          <div className="grid grid-cols-3 gap-4">
            <Field
              label="Total value (sum of all solutions)"
              value={grandSlam.total_value || ""}
              onChange={(v) => update("grand_slam.total_value", v)}
            />
            <Field
              label="Price anchor (cost without you)"
              value={grandSlam.price_anchor || ""}
              onChange={(v) => update("grand_slam.price_anchor", v)}
            />
            <Field
              label="Your price"
              value={grandSlam.actual_price || ""}
              onChange={(v) => update("grand_slam.actual_price", v)}
            />
          </div>
        </div>
      </div>

      {/* Grand Slam Enhancers */}
      <div className="mb-8 rounded-lg border-l-4 border-amber-500 bg-amber-50 p-5">
        <div className="flex items-center gap-3 mb-4">
          <span className="w-8 h-8 rounded-full flex items-center justify-center bg-amber-600 text-white font-bold text-sm">
            +
          </span>
          <h2 className="text-lg font-semibold">Offer Enhancers</h2>
          <span className="text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full font-medium">
            Scarcity + Urgency + Bonuses + Guarantees + Naming
          </span>
        </div>
        <div className="space-y-4">
          <TextArea
            label="Scarcity — Why is this limited?"
            value={enhancers.scarcity || ""}
            onChange={(v) => update("grand_slam.enhancers.scarcity", v)}
            hint="Limited spots, limited access, limited cohort size, only work with X clients per quarter"
          />
          <TextArea
            label="Urgency — Why now?"
            value={enhancers.urgency || ""}
            onChange={(v) => update("grand_slam.enhancers.urgency", v)}
            hint="Deadline, price increase, seasonal, early-bird pricing, founding member rate"
          />
          <ListField
            items={(enhancers.bonuses || []) as string[]}
            onChange={(v) => update("grand_slam.enhancers.bonuses", v)}
            label="Value-stacked bonuses (include $ value for each)"
            placeholder="e.g. Bonus: Hook Library with 200+ templates ($997 value)"
          />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground mb-1 block">
                Guarantee type
              </label>
              <select
                value={enhancers.guarantee_type || ""}
                onChange={(e) =>
                  update("grand_slam.enhancers.guarantee_type", e.target.value)
                }
                className="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              >
                <option value="">Select type...</option>
                <option value="unconditional">
                  Unconditional (money back, no questions)
                </option>
                <option value="conditional">
                  Conditional (money back if you do X and don't get Y)
                </option>
                <option value="anti-guarantee">
                  Anti-Guarantee ("All sales final because...")
                </option>
                <option value="implied">
                  Implied (track record speaks for itself)
                </option>
              </select>
            </div>
            <TextArea
              label="Guarantee statement (exact wording)"
              value={enhancers.guarantee_statement || ""}
              onChange={(v) =>
                update("grand_slam.enhancers.guarantee_statement", v)
              }
              hint="e.g. 'If you don't get 5 qualified leads in 30 days, I'll work with you for free until you do.'"
            />
          </div>
          <Field
            label="Offer name (Hormozi naming formula)"
            value={enhancers.offer_name || ""}
            onChange={(v) => update("grand_slam.enhancers.offer_name", v)}
          />
        </div>
      </div>

      {/* Objections */}
      <Section title="Top Objections">
        <p className="text-sm text-muted-foreground mb-3">
          List the top 5 objections people have and how you respond to each.
        </p>
        <ObjectionList
          items={(offer.objections || []) as Array<{objection: string; response: string}>}
          onChange={(v) => update("objections", v)}
        />
      </Section>

      {/* Why & How (existing fields) */}
      <Section title="Why & How">
        <TextArea
          label="Why does it matter? (List reasons, one per line)"
          value={(offer.why_it_matters || []).join("\n")}
          onChange={(v) => update("why_it_matters", v.split("\n").filter(Boolean))}
          onSuggest={() => suggest("offer.why_it_matters")}
        />
        <TextArea
          label="How does it work? (Step by step, one per line)"
          value={(offer.how_it_works || []).join("\n")}
          onChange={(v) => update("how_it_works", v.split("\n").filter(Boolean))}
          onSuggest={() => suggest("offer.how_it_works")}
        />
        <Field
          label="Timeline to results"
          value={offer.timeline || ""}
          onChange={(v) => update("timeline", v)}
        />
      </Section>

      {/* Proof & Differentiation */}
      <Section title="Proof & Differentiation">
        <TextArea
          label="Past client results"
          value={offer.past_results || ""}
          onChange={(v) => update("past_results", v)}
          onSuggest={() => suggest("offer.past_results")}
        />
        <TextArea
          label="What sets you apart?"
          value={offer.differentiator || ""}
          onChange={(v) => update("differentiator", v)}
          onSuggest={() => suggest("offer.differentiator")}
        />
        <Field
          label="First move (e.g. book a discovery call)"
          value={offer.first_move || ""}
          onChange={(v) => update("first_move", v)}
        />
      </Section>

      {/* Market Research */}
      <Section title="Market Research">
        <TextArea
          label="Niche statement"
          value={market.niche_statement || ""}
          onChange={(v) => update("market.niche_statement", v)}
          onSuggest={() => suggest("offer.market.niche_statement")}
        />
        <TextArea
          label="Massive pains you solve (one per line)"
          value={(market.massive_pains || []).join("\n")}
          onChange={(v) =>
            update("market.massive_pains", v.split("\n").filter(Boolean))
          }
        />
        <TextArea
          label="Leading influencers in your space (one per line)"
          value={(market.leading_influencers || []).join("\n")}
          onChange={(v) =>
            update("market.leading_influencers", v.split("\n").filter(Boolean))
          }
        />
      </Section>

      {/* Framework */}
      <Section title="Your Framework">
        <TextArea
          label="Main steps (one per line)"
          value={(framework.main_steps || []).join("\n")}
          onChange={(v) =>
            update("framework.main_steps", v.split("\n").filter(Boolean))
          }
          onSuggest={() => suggest("offer.framework.main_steps")}
        />
        <Field
          label="Trifecta of power (3 core competencies, comma-separated)"
          value={(framework.trifecta || []).join(", ")}
          onChange={(v) =>
            update(
              "framework.trifecta",
              v.split(",").map((s: string) => s.trim()).filter(Boolean)
            )
          }
        />
        <TextArea
          label="Deliverables (one per line)"
          value={(framework.deliverables || []).join("\n")}
          onChange={(v) =>
            update("framework.deliverables", v.split("\n").filter(Boolean))
          }
        />
      </Section>

      {/* Boosters */}
      <Section title="Offer Boosters">
        <Field
          label="Urgency phrase"
          value={boosters.urgency || ""}
          onChange={(v) => update("boosters.urgency", v)}
        />
        <Field
          label="Guarantee"
          value={boosters.guarantee || ""}
          onChange={(v) => update("boosters.guarantee", v)}
        />
        <Field
          label="Offer name"
          value={boosters.offer_name || ""}
          onChange={(v) => update("boosters.offer_name", v)}
          onSuggest={() => suggest("offer.boosters.offer_name")}
        />
        <TextArea
          label="Bonuses (one per line)"
          value={(boosters.bonuses || []).join("\n")}
          onChange={(v) =>
            update("boosters.bonuses", v.split("\n").filter(Boolean))
          }
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

const MAGIC_COLORS: Record<string, string> = {
  blue: "border-primary bg-primary/15",
  green: "border-green-500 bg-green-50",
  yellow: "border-yellow-500 bg-yellow-50",
  purple: "border-chart-2 bg-chart-2/15",
  red: "border-red-500 bg-red-50",
};

const MAGIC_BADGE_COLORS: Record<string, string> = {
  blue: "bg-primary",
  green: "bg-green-600",
  yellow: "bg-yellow-600",
  purple: "bg-chart-2",
  red: "bg-red-600",
};

function MagicSection({
  letter,
  title,
  color,
  children,
}: {
  letter: string;
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`mb-8 rounded-lg border-l-4 p-5 ${MAGIC_COLORS[color] || ""}`}>
      <div className="flex items-center gap-3 mb-4">
        <span
          className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm ${MAGIC_BADGE_COLORS[color] || "bg-muted"}`}
        >
          {letter}
        </span>
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
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

function ProblemSolutionList({
  items,
  onChange,
}: {
  items: Array<{
    problem: string;
    solution: string;
    delivery_vehicle?: string;
    sexy_name?: string;
  }>;
  onChange: (
    v: Array<{
      problem: string;
      solution: string;
      delivery_vehicle?: string;
      sexy_name?: string;
    }>
  ) => void;
}) {
  const [draftProblem, setDraftProblem] = useState("");
  const [draftSolution, setDraftSolution] = useState("");
  const [draftVehicle, setDraftVehicle] = useState("");
  const [draftName, setDraftName] = useState("");

  const add = () => {
    if (draftProblem.trim() && draftSolution.trim()) {
      onChange([
        ...items,
        {
          problem: draftProblem.trim(),
          solution: draftSolution.trim(),
          delivery_vehicle: draftVehicle.trim() || undefined,
          sexy_name: draftName.trim() || undefined,
        },
      ]);
      setDraftProblem("");
      setDraftSolution("");
      setDraftVehicle("");
      setDraftName("");
    }
  };

  const remove = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div>
      <label className="text-sm font-medium text-muted-foreground mb-1 block">
        Problems &rarr; Solutions &rarr; Delivery &rarr; Sexy Name
      </label>
      <p className="text-xs text-muted-foreground mb-2">
        List every problem your prospect faces. For each, create a solution and
        give it a compelling name (e.g. &quot;The Never-Fall-Off Accountability
        System&quot;).
      </p>
      {items.length > 0 && (
        <div className="space-y-3 mb-4">
          {items.map((item, i) => (
            <div
              key={i}
              className="bg-card border border-border rounded-lg px-4 py-3 text-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-1">
                  <div>
                    <span className="font-medium text-red-600">Problem:</span>{" "}
                    {item.problem}
                  </div>
                  <div>
                    <span className="font-medium text-green-600">
                      Solution:
                    </span>{" "}
                    {item.solution}
                  </div>
                  {item.delivery_vehicle && (
                    <div className="text-muted-foreground">
                      Delivery: {item.delivery_vehicle}
                    </div>
                  )}
                  {item.sexy_name && (
                    <div className="font-medium text-orange-600">
                      &ldquo;{item.sexy_name}&rdquo;
                    </div>
                  )}
                </div>
                <button
                  onClick={() => remove(i)}
                  className="text-muted-foreground hover:text-red-500 text-xs ml-3"
                >
                  remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-2 bg-card border border-border rounded-lg p-3">
        <input
          type="text"
          value={draftProblem}
          onChange={(e) => setDraftProblem(e.target.value)}
          placeholder="Problem: e.g. 'Don't know what to post on LinkedIn'"
          className="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
        />
        <input
          type="text"
          value={draftSolution}
          onChange={(e) => setDraftSolution(e.target.value)}
          placeholder="Solution: e.g. 'Content strategy with pillar system + idea bank'"
          className="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
        />
        <div className="grid grid-cols-2 gap-2">
          <select
            value={draftVehicle}
            onChange={(e) => setDraftVehicle(e.target.value)}
            className="border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          >
            <option value="">Delivery method...</option>
            <option value="1:1">1:1 (Done for you)</option>
            <option value="small group">Small Group</option>
            <option value="1:many">1:Many (Course/Community)</option>
            <option value="DIY">DIY (Self-serve)</option>
            <option value="DWY">DWY (Done with you)</option>
            <option value="DFY">DFY (Done for you)</option>
          </select>
          <input
            type="text"
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            placeholder="Sexy name: e.g. 'The Viral Content Blueprint'"
            className="border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          />
        </div>
        <button
          onClick={add}
          disabled={!draftProblem.trim() || !draftSolution.trim()}
          className="px-4 py-2 bg-orange-100 text-orange-700 rounded-lg text-sm font-medium hover:bg-orange-200 disabled:opacity-50 transition"
        >
          Add Problem &rarr; Solution
        </button>
      </div>
    </div>
  );
}

function ObjectionList({
  items,
  onChange,
}: {
  items: Array<{ objection: string; response: string }>;
  onChange: (v: Array<{ objection: string; response: string }>) => void;
}) {
  const [draftObjection, setDraftObjection] = useState("");
  const [draftResponse, setDraftResponse] = useState("");

  const add = () => {
    if (draftObjection.trim() && draftResponse.trim()) {
      onChange([
        ...items,
        { objection: draftObjection.trim(), response: draftResponse.trim() },
      ]);
      setDraftObjection("");
      setDraftResponse("");
    }
  };

  const remove = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div>
      {items.length > 0 && (
        <div className="space-y-3 mb-4">
          {items.map((item, i) => (
            <div
              key={i}
              className="bg-card border border-border rounded-lg px-4 py-3 text-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-medium text-red-600 mb-1">
                    &ldquo;{item.objection}&rdquo;
                  </div>
                  <div className="text-foreground">{item.response}</div>
                </div>
                <button
                  onClick={() => remove(i)}
                  className="text-muted-foreground hover:text-red-500 text-xs ml-3"
                >
                  remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-2">
        <input
          type="text"
          value={draftObjection}
          onChange={(e) => setDraftObjection(e.target.value)}
          placeholder="Objection: e.g. 'It's too expensive'"
          className="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
        />
        <input
          type="text"
          value={draftResponse}
          onChange={(e) => setDraftResponse(e.target.value)}
          placeholder="Your response: e.g. 'Compare to a full-time hire at $6K/month'"
          className="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
        />
        <button
          onClick={add}
          disabled={!draftObjection.trim() || !draftResponse.trim()}
          className="px-4 py-2 bg-muted text-muted-foreground rounded-lg text-sm font-medium hover:bg-accent disabled:opacity-50 transition"
        >
          Add Objection
        </button>
      </div>
    </div>
  );
}
