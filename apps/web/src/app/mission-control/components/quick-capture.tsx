"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function QuickCapture() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const actions = [
    {
      icon: "✍️",
      label: "Write a post",
      description: "Open the Composer",
      onClick: () => { setOpen(false); router.push("/composer"); },
    },
    {
      icon: "💡",
      label: "Save an idea",
      description: "Add to Inspo board",
      onClick: () => { setOpen(false); router.push("/inspo"); },
    },
    {
      icon: "🎙️",
      label: "Voice note",
      description: "Send to Jumbo via Telegram",
      onClick: () => {
        setOpen(false);
        window.open("https://t.me/Jumbohere_bot", "_blank", "noopener,noreferrer");
      },
    },
  ];

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(true)}
        aria-label="Quick capture"
        className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-amber-500 text-black text-xl font-bold shadow-lg hover:bg-amber-400 transition flex items-center justify-center"
      >
        +
      </button>

      {/* Modal */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-end pb-24 pr-6"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />

          {/* Menu */}
          <div className="relative z-10 w-56 rounded-2xl border border-border bg-card shadow-2xl overflow-hidden">
            {actions.map((action) => (
              <button
                key={action.label}
                onClick={action.onClick}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-accent transition text-left"
              >
                <span className="text-lg w-6 text-center">{action.icon}</span>
                <div>
                  <div className="text-sm font-medium text-foreground">{action.label}</div>
                  <div className="text-[10px] text-muted-foreground">{action.description}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
