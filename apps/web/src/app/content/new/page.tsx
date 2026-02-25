"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { trackEvent } from "@/lib/posthog";
import { contentApi, personalBrandsApi } from "../../../lib/api";
import { useBrand } from "@/lib/brand-context";

/* ────────────────────────────────────────────────────────────
   Content Objectives (Poppy-style visual cards)
   ──────────────────────────────────────────────────────────── */

const OBJECTIVES = [
  {
    id: "personal_branding",
    label: "Personal Branding",
    description: "Position yourself as the go-to authority in your niche",
    color: "from-violet-500 to-purple-600",
    bgLight: "bg-violet-500/10 border-violet-500/30",
    textColor: "text-violet-400",
    icon: (
      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
      </svg>
    ),
  },
  {
    id: "sales",
    label: "Drive Sales",
    description: "Convert viewers into leads, calls, and customers",
    color: "from-emerald-500 to-green-600",
    bgLight: "bg-emerald-500/10 border-emerald-500/30",
    textColor: "text-emerald-400",
    icon: (
      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    id: "grow_audience",
    label: "Grow Audience",
    description: "Attract new followers and expand your reach organically",
    color: "from-blue-500 to-indigo-600",
    bgLight: "bg-blue-500/10 border-blue-500/30",
    textColor: "text-blue-400",
    icon: (
      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
      </svg>
    ),
  },
  {
    id: "educate",
    label: "Educate",
    description: "Teach your audience something valuable they can apply today",
    color: "from-amber-500 to-orange-600",
    bgLight: "bg-amber-500/10 border-amber-500/30",
    textColor: "text-amber-400",
    icon: (
      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
      </svg>
    ),
  },
  {
    id: "entertainment",
    label: "Entertain",
    description: "Create content that hooks and holds attention through storytelling",
    color: "from-pink-500 to-rose-600",
    bgLight: "bg-pink-500/10 border-pink-500/30",
    textColor: "text-pink-400",
    icon: (
      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-2.133-1.001A3.75 3.75 0 0012 18z" />
      </svg>
    ),
  },
];

/* ────────────────────────────────────────────────────────────
   Content Types (pill-style selectors)
   ──────────────────────────────────────────────────────────── */

const CONTENT_TYPES = [
  { id: "educational", label: "Educational", emoji: "📚" },
  { id: "storytelling", label: "Storytelling", emoji: "📖" },
  { id: "opinion", label: "Hot Take / Opinion", emoji: "🔥" },
  { id: "how_to", label: "How-To / Tutorial", emoji: "🛠" },
  { id: "listicle", label: "Listicle", emoji: "📝" },
  { id: "contrarian", label: "Contrarian / Myth-Busting", emoji: "💥" },
  { id: "case_study", label: "Case Study", emoji: "📊" },
  { id: "behind_scenes", label: "Behind the Scenes", emoji: "🎬" },
];

/* ────────────────────────────────────────────────────────────
   Platforms
   ──────────────────────────────────────────────────────────── */

const PLATFORMS = [
  {
    id: "youtube",
    label: "YouTube",
    description: "Long-form script + Shorts + titles, description, tags",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
      </svg>
    ),
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    description: "3 post variants: story, list, and contrarian",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
      </svg>
    ),
  },
  {
    id: "twitter",
    label: "Twitter/X",
    description: "3 standalone posts + 1 thread",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    ),
  },
  {
    id: "short_form",
    label: "Short-form",
    description: "TikTok, Reels, and Shorts (30-60s)",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="6" y="3" width="12" height="18" rx="2" />
        <line x1="10" y1="17" x2="14" y2="17" />
      </svg>
    ),
  },
];

/* ────────────────────────────────────────────────────────────
   Tone Options
   ──────────────────────────────────────────────────────────── */

const TONES = [
  { id: "conversational", label: "Conversational", emoji: "💬", description: "Friendly, relatable, like talking to a friend" },
  { id: "professional", label: "Professional", emoji: "👔", description: "Polished and credible, business-ready" },
  { id: "authoritative", label: "Authoritative", emoji: "🎯", description: "Expert-level confidence, backed by proof" },
  { id: "casual", label: "Casual", emoji: "😎", description: "Relaxed and approachable, low-key vibe" },
  { id: "bold", label: "Bold / Provocative", emoji: "🔥", description: "Strong opinions, challenges the status quo" },
  { id: "inspirational", label: "Inspirational", emoji: "✨", description: "Motivating, uplifting, calls to action" },
];

/* ────────────────────────────────────────────────────────────
   Content Length Options
   ──────────────────────────────────────────────────────────── */

const LENGTHS = [
  { id: "short", label: "Short", detail: "YouTube: 5-8 min | LinkedIn: 150-300 words | Twitter: single tweet" },
  { id: "medium", label: "Medium", detail: "YouTube: 10-15 min | LinkedIn: 400-800 words | Twitter: short thread" },
  { id: "long", label: "Long", detail: "YouTube: 20-30 min | LinkedIn: 1000+ words | Twitter: full thread" },
  { id: "auto", label: "Auto (AI decides)", detail: "Let the AI pick the ideal length for your topic and platform" },
];

const RESEARCH_SOURCES = [
  { id: "youtube", label: "YouTube trends", icon: "📺" },
  { id: "reddit", label: "Reddit discussions", icon: "💬" },
  { id: "newsletters", label: "Newsletters", icon: "📩" },
  { id: "news", label: "News", icon: "📰" },
  { id: "user_resources", label: "My Knowledge Base", icon: "📗" },
];

/* ────────────────────────────────────────────────────────────
   Component
   ──────────────────────────────────────────────────────────── */

export default function NewWorkflow() {
  const router = useRouter();
  const { brandId } = useBrand();
  // Form state
  const [objective, setObjective] = useState("");
  const [contentType, setContentType] = useState("");
  const [goalText, setGoalText] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["youtube"]);
  const [tone, setTone] = useState("conversational");
  const [contentLength, setContentLength] = useState("auto");
  const [selectedPillars, setSelectedPillars] = useState<string[]>([]);
  const [customPillar, setCustomPillar] = useState("");
  const [brandPillars, setBrandPillars] = useState<string[]>([]);
  const [sources, setSources] = useState<Record<string, boolean>>({
    youtube: true,
    reddit: true,
    newsletters: true,
    news: true,
    user_resources: true,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Load content pillars from brand profile
  useEffect(() => {
    if (!brandId) return;
    personalBrandsApi.get(brandId).then((brand: any) => {
      const pj = brand?.profile_json || {};
      const pillars = pj?.foundation?.content_pillars || pj?.content_pillars || [];
      if (pillars.length > 0) {
        setBrandPillars(pillars);
        setSelectedPillars(pillars);
      }
    }).catch(() => {
      // Non-critical, ignore
    });
  }, [brandId]);

  const togglePlatform = (id: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const toggleSource = (id: string) => {
    setSources((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const canSubmit =
    objective && contentType && goalText.trim() && selectedPlatforms.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError("");

    try {
      const result = await contentApi.create({
        goal_text: goalText.trim(),
        platforms: selectedPlatforms,
        settings: {
          sources,
          objective,
          content_type: contentType,
          tone,
          content_length: contentLength,
          content_pillars: selectedPillars,
        },
        brand_id: brandId || undefined,
      });
      trackEvent("content_workflow_started", {
        objective,
        content_type: contentType,
        platforms: selectedPlatforms,
        tone,
        content_length: contentLength,
        brand_id: brandId || "",
      });
      router.push(`/content/${result.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create workflow");
      setSubmitting(false);
    }
  };

  return (
    <main className="max-w-3xl mx-auto px-6 py-10 bg-zinc-950 text-zinc-100 min-h-screen">
      {/* Header */}
      <div className="mb-10">
        <Link
          href="/content"
          className="inline-flex items-center text-sm text-zinc-500 hover:text-zinc-300 transition mb-4"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          Back to Content
        </Link>
        <h1 className="text-3xl font-bold text-zinc-100">Create New Content</h1>
        <p className="text-zinc-400 mt-2 text-base">
          Choose your goal, pick a format, and tell the AI what to write. It will research, find angles, generate hooks, and build the full content pack.
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-8 text-red-400 text-sm flex items-start gap-3">
          <svg className="w-5 h-5 mt-0.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-10">

        {/* ───── Step 1: Content Objective ───── */}
        <section>
          <div className="flex items-center gap-2 mb-1">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-zinc-100 text-zinc-900 text-xs font-bold">1</span>
            <h2 className="text-lg font-semibold text-zinc-100">What is your goal?</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-4">
            Pick the primary objective for this content piece.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 ml-8">
            {OBJECTIVES.map((obj) => {
              const selected = objective === obj.id;
              return (
                <button
                  key={obj.id}
                  type="button"
                  onClick={() => setObjective(obj.id)}
                  className={`relative flex flex-col items-start p-4 rounded-xl border-2 text-left transition-all duration-200 group ${
                    selected
                      ? `${obj.bgLight} border-current ${obj.textColor}`
                      : "border-zinc-700 bg-zinc-900 hover:border-zinc-600"
                  }`}
                >
                  {/* Selected indicator */}
                  {selected && (
                    <div className="absolute top-3 right-3">
                      <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                      </svg>
                    </div>
                  )}

                  <div className={`mb-3 p-2 rounded-lg ${selected ? "bg-white/10" : "bg-zinc-800 group-hover:bg-zinc-700"} transition`}>
                    <div className={selected ? obj.textColor : "text-zinc-500 group-hover:text-zinc-400"}>
                      {obj.icon}
                    </div>
                  </div>
                  <div className={`text-sm font-semibold mb-1 ${selected ? obj.textColor : "text-zinc-200"}`}>
                    {obj.label}
                  </div>
                  <div className="text-xs text-zinc-500 leading-relaxed">
                    {obj.description}
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* ───── Step 2: Content Type ───── */}
        <section className={`transition-opacity duration-300 ${objective ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${objective ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-500"}`}>2</span>
            <h2 className="text-lg font-semibold text-zinc-100">Content style</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-4">
            How do you want to frame the message?
          </p>

          <div className="flex flex-wrap gap-2 ml-8">
            {CONTENT_TYPES.map((ct) => {
              const selected = contentType === ct.id;
              return (
                <button
                  key={ct.id}
                  type="button"
                  onClick={() => setContentType(ct.id)}
                  className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium border-2 transition-all duration-200 ${
                    selected
                      ? "border-zinc-100 bg-zinc-100 text-zinc-900"
                      : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800"
                  }`}
                >
                  <span className="text-base">{ct.emoji}</span>
                  {ct.label}
                </button>
              );
            })}
          </div>
        </section>

        {/* ───── Step 3: Platforms ───── */}
        <section className={`transition-opacity duration-300 ${contentType ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${contentType ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-500"}`}>3</span>
            <h2 className="text-lg font-semibold text-zinc-100">Where to publish?</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-4">
            Select at least one platform. The AI adapts format and length for each.
          </p>

          <div className="grid grid-cols-2 gap-3 ml-8">
            {PLATFORMS.map((p) => {
              const selected = selectedPlatforms.includes(p.id);
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => togglePlatform(p.id)}
                  className={`flex items-center gap-3 p-3.5 rounded-xl border-2 text-left transition-all duration-200 ${
                    selected
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-zinc-700 bg-zinc-900 hover:border-zinc-600"
                  }`}
                >
                  <div className={`p-2 rounded-lg ${selected ? "bg-blue-500/20 text-blue-400" : "bg-zinc-800 text-zinc-500"} transition`}>
                    {p.icon}
                  </div>
                  <div className="min-w-0">
                    <div className={`text-sm font-medium ${selected ? "text-blue-300" : "text-zinc-200"}`}>
                      {p.label}
                    </div>
                    <div className="text-xs text-zinc-500 truncate">{p.description}</div>
                  </div>
                  {selected && (
                    <svg className="w-5 h-5 ml-auto text-blue-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              );
            })}
          </div>
        </section>

        {/* ───── Step 4: Topic / Goal ───── */}
        <section className={`transition-opacity duration-300 ${contentType ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${contentType ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-500"}`}>4</span>
            <h2 className="text-lg font-semibold text-zinc-100">What is it about?</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-3">
            Be specific about the topic, angle, and audience. The more detail, the better the output.
          </p>

          <div className="ml-8">
            <textarea
              value={goalText}
              onChange={(e) => setGoalText(e.target.value)}
              placeholder="e.g. How to build a personal brand on LinkedIn in 2026, targeting solopreneurs who are stuck at under 1000 followers..."
              className="w-full border-2 border-zinc-700 bg-zinc-900 text-zinc-100 rounded-xl p-4 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition placeholder:text-zinc-500"
              rows={4}
              maxLength={2000}
            />
            <div className="flex items-center justify-between mt-1.5">
              <p className="text-xs text-zinc-500">
                Be specific about topic, angle, and target audience.
              </p>
              <p className="text-xs text-zinc-500">
                {goalText.length}/2000
              </p>
            </div>
          </div>
        </section>

        {/* ───── Step 5: Tone ───── */}
        <section className={`transition-opacity duration-300 ${contentType ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${contentType ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-500"}`}>5</span>
            <h2 className="text-lg font-semibold text-zinc-100">Tone of voice</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-3">
            How should this content sound? This overrides the default from your brand profile for this piece.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 ml-8">
            {TONES.map((t) => {
              const selected = tone === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTone(t.id)}
                  className={`flex items-start gap-2 p-3 rounded-xl border-2 text-left transition-all duration-200 ${
                    selected
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-zinc-700 bg-zinc-900 hover:border-zinc-600"
                  }`}
                >
                  <span className="text-lg mt-0.5">{t.emoji}</span>
                  <div className="min-w-0">
                    <div className={`text-sm font-medium ${selected ? "text-blue-300" : "text-zinc-200"}`}>
                      {t.label}
                    </div>
                    <div className="text-xs text-zinc-500 leading-snug">{t.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* ───── Step 6: Content Length ───── */}
        <section className={`transition-opacity duration-300 ${contentType ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${contentType ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-500"}`}>6</span>
            <h2 className="text-lg font-semibold text-zinc-100">Content length</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-3">
            How long should the content be? Length adapts to each platform automatically.
          </p>

          <div className="space-y-2 ml-8">
            {LENGTHS.map((l) => {
              const selected = contentLength === l.id;
              return (
                <button
                  key={l.id}
                  type="button"
                  onClick={() => setContentLength(l.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 text-left transition-all duration-200 ${
                    selected
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-zinc-700 bg-zinc-900 hover:border-zinc-600"
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                    selected ? "border-blue-500" : "border-zinc-600"
                  }`}>
                    {selected && <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />}
                  </div>
                  <div className="min-w-0">
                    <div className={`text-sm font-medium ${selected ? "text-blue-300" : "text-zinc-200"}`}>
                      {l.label}
                    </div>
                    <div className="text-xs text-zinc-500">{l.detail}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* ───── Step 7: Content Pillars ───── */}
        <section className={`transition-opacity duration-300 ${contentType ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${contentType ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-500"}`}>7</span>
            <h2 className="text-lg font-semibold text-zinc-100">Content pillars</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-3">
            {brandPillars.length > 0
              ? "Your brand pillars are pre-loaded. Toggle them on or off, or add new ones for this piece."
              : "Add the themes and topics this content should cover. You can set default pillars in your brand profile."}
          </p>

          <div className="ml-8 space-y-3">
            {/* Existing pillars */}
            {(brandPillars.length > 0 || selectedPillars.length > 0) && (
              <div className="flex flex-wrap gap-2">
                {[...new Set([...brandPillars, ...selectedPillars])].map((pillar) => {
                  const isSelected = selectedPillars.includes(pillar);
                  return (
                    <button
                      key={pillar}
                      type="button"
                      onClick={() => {
                        setSelectedPillars((prev) =>
                          prev.includes(pillar)
                            ? prev.filter((p) => p !== pillar)
                            : [...prev, pillar]
                        );
                      }}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-all duration-200 ${
                        isSelected
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 font-medium"
                          : "border-zinc-700 bg-zinc-900 text-zinc-500 hover:border-zinc-600 line-through"
                      }`}
                    >
                      {pillar}
                      {isSelected && (
                        <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Add new pillar */}
            <div className="flex gap-2">
              <input
                type="text"
                value={customPillar}
                onChange={(e) => setCustomPillar(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && customPillar.trim()) {
                    e.preventDefault();
                    const trimmed = customPillar.trim();
                    if (!selectedPillars.includes(trimmed)) {
                      setSelectedPillars((prev) => [...prev, trimmed]);
                    }
                    setCustomPillar("");
                  }
                }}
                placeholder="Add a pillar (e.g., Leadership, AI, Marketing)..."
                className="flex-1 border-2 border-zinc-700 bg-zinc-900 text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition placeholder:text-zinc-500"
              />
              <button
                type="button"
                onClick={() => {
                  const trimmed = customPillar.trim();
                  if (trimmed && !selectedPillars.includes(trimmed)) {
                    setSelectedPillars((prev) => [...prev, trimmed]);
                    setCustomPillar("");
                  }
                }}
                disabled={!customPillar.trim()}
                className="px-3 py-2 bg-zinc-800 text-zinc-300 rounded-lg text-sm hover:bg-zinc-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Add
              </button>
            </div>
          </div>
        </section>

        {/* ───── Step 8: Research Sources ───── */}
        <section className={`transition-opacity duration-300 ${contentType ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${contentType ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-500"}`}>8</span>
            <h2 className="text-lg font-semibold text-zinc-100">Research sources</h2>
          </div>
          <p className="text-sm text-zinc-500 ml-8 mb-3">
            The AI searches these for trends, gaps, and content ideas before writing.
          </p>

          <div className="flex flex-wrap gap-2 ml-8">
            {RESEARCH_SOURCES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => toggleSource(s.id)}
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-sm border transition-all duration-200 ${
                  sources[s.id]
                    ? "border-blue-500/40 bg-blue-500/10 text-blue-400 font-medium"
                    : "border-zinc-700 bg-zinc-900 text-zinc-500 hover:border-zinc-600"
                }`}
              >
                <span>{s.icon}</span>
                {s.label}
              </button>
            ))}
          </div>
        </section>

        {/* ───── Submit ───── */}
        <div className="flex items-center gap-4 pt-2 ml-8">
          <button
            type="submit"
            disabled={submitting || !canSubmit}
            className="px-8 py-3 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Creating...
              </span>
            ) : (
              <>Create Content &rarr;</>
            )}
          </button>
          <Link
            href="/content"
            className="text-sm text-zinc-500 hover:text-zinc-300 transition"
          >
            Cancel
          </Link>
        </div>

        {/* ───── Summary preview ───── */}
        {canSubmit && (
          <div className="ml-8 p-4 rounded-xl bg-zinc-900 border border-zinc-800">
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Summary</p>
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="px-2 py-1 rounded-md bg-violet-500/20 text-violet-400 font-medium">
                {OBJECTIVES.find((o) => o.id === objective)?.label}
              </span>
              <span className="px-2 py-1 rounded-md bg-zinc-800 text-zinc-300 font-medium">
                {CONTENT_TYPES.find((c) => c.id === contentType)?.emoji}{" "}
                {CONTENT_TYPES.find((c) => c.id === contentType)?.label}
              </span>
              {selectedPlatforms.map((pid) => (
                <span key={pid} className="px-2 py-1 rounded-md bg-blue-500/20 text-blue-400 font-medium">
                  {PLATFORMS.find((p) => p.id === pid)?.label}
                </span>
              ))}
              <span className="px-2 py-1 rounded-md bg-amber-500/20 text-amber-400 font-medium">
                {TONES.find((t) => t.id === tone)?.emoji} {TONES.find((t) => t.id === tone)?.label}
              </span>
              <span className="px-2 py-1 rounded-md bg-cyan-500/20 text-cyan-400 font-medium">
                {LENGTHS.find((l) => l.id === contentLength)?.label}
              </span>
              {selectedPillars.length > 0 && (
                <span className="px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-400 font-medium">
                  {selectedPillars.length} pillar{selectedPillars.length !== 1 ? "s" : ""}
                </span>
              )}
              <span className="px-2 py-1 rounded-md bg-green-500/20 text-green-400 font-medium">
                {Object.values(sources).filter(Boolean).length} sources
              </span>
            </div>
          </div>
        )}
      </form>
    </main>
  );
}
