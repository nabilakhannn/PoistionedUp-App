"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { personalBrandsApi } from "@/lib/api/brand";

type Step = 1 | 2 | 3 | 4;

const ROLES = [
  "Founder",
  "Executive",
  "Creator",
  "Consultant",
  "Other",
] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1
  const [name, setName] = useState("");
  const [role, setRole] = useState<string>("");
  const [goal, setGoal] = useState("");

  // Step 2
  const [post1, setPost1] = useState("");
  const [post2, setPost2] = useState("");
  const [post3, setPost3] = useState("");

  // Persisted brand id across steps
  const [brandId, setBrandId] = useState<string | null>(null);

  // ── Step 1: create brand ───────────────────────────────
  const handleStep1 = async () => {
    if (!name.trim()) { setError("Please enter your name."); return; }
    setSaving(true);
    setError(null);
    try {
      const brand = await personalBrandsApi.create({
        name: name.trim(),
        description: role ? `${role}${goal ? ` — ${goal}` : ""}` : goal || undefined,
      });
      setBrandId(brand.id);
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create profile");
    } finally {
      setSaving(false);
    }
  };

  // ── Step 2: save voice samples ─────────────────────────
  const handleStep2 = async () => {
    if (!brandId) { setStep(3); return; }
    const beliefs = [post1, post2, post3].map((p) => p.trim()).filter(Boolean);
    setSaving(true);
    setError(null);
    try {
      if (beliefs.length > 0) {
        await personalBrandsApi.updateFoundation(brandId, { beliefs });
      }
      setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save voice samples");
    } finally {
      setSaving(false);
    }
  };

  // ── Step 4: finish onboarding ──────────────────────────
  const handleFinish = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("onboarding_done", "1");
    }
    router.push("/mission-control");
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-lg">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between mb-2">
            {[1, 2, 3, 4].map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition ${
                    s < step
                      ? "bg-amber-500 border-amber-500 text-black"
                      : s === step
                      ? "border-amber-500 text-amber-400"
                      : "border-border text-muted-foreground"
                  }`}
                >
                  {s < step ? "✓" : s}
                </div>
                {s < 4 && (
                  <div
                    className={`flex-1 h-0.5 w-16 transition ${
                      s < step ? "bg-amber-500" : "bg-border"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground text-center">
            Step {step} of 4
          </p>
        </div>

        {/* Step 1 — Who are you? */}
        {step === 1 && (
          <div className="space-y-5">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Who are you?</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Tell us a bit about yourself so your agent can write in your voice.
              </p>
            </div>

            <div>
              <label className="block text-xs text-muted-foreground uppercase tracking-wider mb-1.5">
                Your name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Sarah Chen"
                className="w-full bg-accent border border-border rounded-lg px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-amber-500/60"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs text-muted-foreground uppercase tracking-wider mb-1.5">
                Your role
              </label>
              <div className="flex flex-wrap gap-2">
                {ROLES.map((r) => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                      role === r
                        ? "bg-amber-500/20 border-amber-500/40 text-amber-400"
                        : "border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs text-muted-foreground uppercase tracking-wider mb-1.5">
                Primary goal <span className="text-muted-foreground/50">(optional)</span>
              </label>
              <input
                type="text"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g. Grow my LinkedIn following to 10k"
                className="w-full bg-accent border border-border rounded-lg px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-amber-500/60"
              />
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button
              onClick={handleStep1}
              disabled={!name.trim() || saving}
              className="w-full py-3 rounded-lg bg-amber-500 text-black font-bold text-sm hover:bg-amber-400 disabled:opacity-40 transition"
            >
              {saving ? "Creating profile..." : "Continue →"}
            </button>
          </div>
        )}

        {/* Step 2 — Brand voice */}
        {step === 2 && (
          <div className="space-y-5">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Your brand voice</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Paste up to 3 of your best posts — the Writer agent will match this style.
              </p>
            </div>

            {[
              { label: "Post #1", value: post1, setter: setPost1 },
              { label: "Post #2", value: post2, setter: setPost2 },
              { label: "Post #3", value: post3, setter: setPost3 },
            ].map(({ label, value, setter }) => (
              <div key={label}>
                <label className="block text-xs text-muted-foreground uppercase tracking-wider mb-1.5">
                  {label} <span className="text-muted-foreground/50">(optional)</span>
                </label>
                <textarea
                  value={value}
                  onChange={(e) => setter(e.target.value)}
                  placeholder="Paste a post here..."
                  className="w-full bg-accent border border-border rounded-lg px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-amber-500/60 resize-none h-24"
                />
              </div>
            ))}

            {error && <p className="text-xs text-red-400">{error}</p>}

            <div className="flex gap-3">
              <button
                onClick={() => setStep(3)}
                className="flex-1 py-3 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground transition"
              >
                Skip for now
              </button>
              <button
                onClick={handleStep2}
                disabled={saving}
                className="flex-1 py-3 rounded-lg bg-amber-500 text-black font-bold text-sm hover:bg-amber-400 disabled:opacity-40 transition"
              >
                {saving ? "Saving..." : "Continue →"}
              </button>
            </div>
          </div>
        )}

        {/* Step 3 — Connect Telegram */}
        {step === 3 && (
          <div className="space-y-5">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Connect Telegram</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Send voice notes or text to Jumbo — your AI chief of staff — directly in Telegram.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-5 space-y-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center text-2xl">
                ✈️
              </div>
              <div>
                <div className="font-semibold text-sm">@Jumbohere_bot</div>
                <div className="text-xs text-muted-foreground">
                  Send voice notes, ideas, or questions — Jumbo turns them into content.
                </div>
              </div>
              <a
                href="https://t.me/Jumbohere_bot"
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full py-2.5 rounded-lg bg-blue-500/20 border border-blue-500/30 text-blue-400 text-sm font-medium text-center hover:bg-blue-500/30 transition"
              >
                Open @Jumbohere_bot in Telegram
              </a>
            </div>

            <p className="text-xs text-muted-foreground">
              You can also connect LinkedIn and Twitter later in Settings.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(4)}
                className="flex-1 py-3 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground transition"
              >
                Skip for now
              </button>
              <button
                onClick={() => setStep(4)}
                className="flex-1 py-3 rounded-lg bg-amber-500 text-black font-bold text-sm hover:bg-amber-400 transition"
              >
                Connected →
              </button>
            </div>
          </div>
        )}

        {/* Step 4 — You're all set */}
        {step === 4 && (
          <div className="space-y-6 text-center">
            <div className="text-5xl">🎉</div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">You&apos;re all set!</h1>
              <p className="text-sm text-muted-foreground mt-2">
                Your agents are ready to start working for you.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-5 space-y-3 text-left">
              {[
                { icon: "🎙️", text: "Send a voice note → Jumbo drafts a post" },
                { icon: "☀️", text: "Get an 8am briefing every morning" },
                { icon: "✋", text: "Nothing posts without your approval" },
              ].map(({ icon, text }) => (
                <div key={text} className="flex items-start gap-3">
                  <span className="text-lg leading-tight">{icon}</span>
                  <span className="text-sm text-foreground">{text}</span>
                </div>
              ))}
            </div>

            <button
              onClick={handleFinish}
              className="w-full py-3 rounded-lg bg-amber-500 text-black font-bold text-sm hover:bg-amber-400 transition"
            >
              Open Mission Control →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
