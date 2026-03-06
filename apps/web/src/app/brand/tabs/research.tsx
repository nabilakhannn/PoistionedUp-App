"use client";

import Link from "next/link";

const RESEARCH_MODES = [
  {
    id: "ai",
    icon: "🤖",
    title: "AI Research",
    subtitle: "Do it for me",
    desc: "Provide your name, LinkedIn URL, and website. AI does the rest in ~30 seconds.",
    cta: "Start",
    href: (brandId: string) => `/brands/${brandId}?mode=ai`,
  },
  {
    id: "guided",
    icon: "🧭",
    title: "Guided Research",
    subtitle: "Interview me",
    desc: "Jumbo asks you questions and fills your profile from your answers. Conversational and thorough.",
    cta: "Begin Chat",
    href: (brandId: string) => `/brands/${brandId}/strategist`,
  },
  {
    id: "manual",
    icon: "✍️",
    title: "Deep Dive",
    subtitle: "I'll fill it in",
    desc: "Full 8-section forms. You see every field. Most thorough option.",
    cta: "Open Forms",
    href: (brandId: string) => `/brands/${brandId}`,
  },
];

export function BrandResearchTab({ brandId }: { brandId: string }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm font-semibold text-zinc-200">Research Your Brand</h2>
        <p className="text-xs text-zinc-500 mt-0.5">Choose how to build your brand profile. All modes produce the same 8-section dossier.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {RESEARCH_MODES.map((mode) => (
          <div key={mode.id} className="glass-card flex flex-col justify-between">
            <div>
              <span className="text-2xl">{mode.icon}</span>
              <h3 className="text-sm font-semibold text-zinc-200 mt-3">{mode.title}</h3>
              <p className="text-xs text-violet-400/80 font-medium">{mode.subtitle}</p>
              <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{mode.desc}</p>
            </div>
            <Link href={mode.href(brandId)} className="glass-button-primary text-sm mt-4 text-center">
              {mode.cta} →
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
