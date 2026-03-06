"use client";

import Link from "next/link";
import { useBrand } from "@/lib/brand-context";

const VIDEO_OPTIONS = [
  {
    id: "avatar",
    icon: "🎤",
    title: "AI Avatar",
    desc: "HeyGen talking head. Pick an avatar, voice, and emotion. AI reads your script on camera.",
    cta: "Create",
    available: false,
  },
  {
    id: "ai-video",
    icon: "🎬",
    title: "AI Video",
    desc: "Veo3.1 faceless viral content. Text or image to video. AI generates the full video.",
    cta: "Create",
    available: false,
  },
  {
    id: "script",
    icon: "📝",
    title: "Script Only",
    desc: "Just the script — you record yourself or use your own tools. Speaker notes + visual cues included.",
    cta: "Write",
    available: true,
  },
];

export default function ContentVideoPage() {
  const { currentBrand } = useBrand();

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400">Select a brand first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-4xl mx-auto px-5 py-8 space-y-6">
        <div>
          <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
          <h1 className="text-xl font-bold text-zinc-100 mt-1">Video Content</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Choose how to create your video.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {VIDEO_OPTIONS.map((opt) => (
            <div
              key={opt.id}
              className={`glass-card flex flex-col justify-between ${!opt.available ? "opacity-60" : ""}`}
            >
              <div>
                <span className="text-2xl">{opt.icon}</span>
                <h3 className="text-sm font-semibold text-zinc-200 mt-3">{opt.title}</h3>
                <p className="text-xs text-zinc-500 mt-1.5 leading-relaxed">{opt.desc}</p>
              </div>
              <div className="mt-4">
                {opt.available ? (
                  <button className="glass-button-primary text-sm w-full">
                    {opt.cta} →
                  </button>
                ) : (
                  <div className="text-center">
                    <span className="glass-badge text-[10px]">Coming soon</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="glass-card text-center py-6">
          <p className="text-xs text-zinc-500">
            AI Avatar (HeyGen) and AI Video (Veo3.1) require API keys.
            Add them in <Link href="/brand?tab=settings" className="text-violet-400 hover:text-violet-300">Brand Settings</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}
