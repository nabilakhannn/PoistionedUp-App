"use client";

import { ReactNode, useState, useEffect } from "react";

interface ComposerLayoutProps {
  sidebar: ReactNode;
  editor: ReactNode;
  preview: ReactNode;
  sidebarCollapsed?: boolean;
  previewCollapsed?: boolean;
}

export function ComposerLayout({
  sidebar,
  editor,
  preview,
  sidebarCollapsed: initialSidebarCollapsed = false,
  previewCollapsed: initialPreviewCollapsed = false,
}: ComposerLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(initialSidebarCollapsed);
  const [previewCollapsed, setPreviewCollapsed] = useState(initialPreviewCollapsed);
  const [mobilePanel, setMobilePanel] = useState<"sidebar" | "editor" | "preview">("editor");
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
      setIsMobile(e.matches);
      if (e.matches) {
        setMobilePanel("editor");
      }
    };
    handleChange(mq);
    mq.addEventListener("change", handleChange as (e: MediaQueryListEvent) => void);
    return () => mq.removeEventListener("change", handleChange as (e: MediaQueryListEvent) => void);
  }, []);

  // ── Mobile layout: single panel with bottom nav ──
  if (isMobile) {
    return (
      <div className="flex flex-col h-[calc(100vh-64px)] bg-zinc-950">
        <div className="flex-1 overflow-y-auto">
          {mobilePanel === "sidebar" && <div className="p-3">{sidebar}</div>}
          {mobilePanel === "editor" && (
            <div className="p-4">{editor}</div>
          )}
          {mobilePanel === "preview" && <div className="p-3">{preview}</div>}
        </div>
        {/* Bottom tab bar */}
        <nav className="flex border-t border-zinc-800 bg-zinc-900 flex-shrink-0">
          <MobileTab
            icon="📊"
            label="Pipeline"
            active={mobilePanel === "sidebar"}
            onClick={() => setMobilePanel("sidebar")}
          />
          <MobileTab
            icon="✏️"
            label="Editor"
            active={mobilePanel === "editor"}
            onClick={() => setMobilePanel("editor")}
          />
          <MobileTab
            icon="👀"
            label="Preview"
            active={mobilePanel === "preview"}
            onClick={() => setMobilePanel("preview")}
          />
        </nav>
      </div>
    );
  }

  // ── Desktop layout: 3-panel ──
  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-zinc-950">
      {/* LEFT SIDEBAR */}
      <aside
        className={`border-r border-zinc-800 transition-all duration-200 flex-shrink-0 overflow-y-auto ${
          sidebarCollapsed ? "w-14" : "w-72"
        }`}
      >
        <div className="sticky top-0 z-10 bg-zinc-950 border-b border-zinc-800 px-2 py-2 flex items-center justify-end">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="text-zinc-500 hover:text-zinc-300 p-1 rounded transition-colors"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? "▶" : "◀"}
          </button>
        </div>
        {!sidebarCollapsed && <div className="p-3">{sidebar}</div>}
        {sidebarCollapsed && (
          <div className="flex flex-col items-center py-2 gap-1">
            <SidebarIcon icon="📊" label="Pipeline" onClick={() => setSidebarCollapsed(false)} />
            <SidebarIcon icon="🧠" label="Context" onClick={() => setSidebarCollapsed(false)} />
            <SidebarIcon icon="📈" label="Insights" onClick={() => setSidebarCollapsed(false)} />
            <SidebarIcon icon="🔧" label="Tools" onClick={() => setSidebarCollapsed(false)} />
            <SidebarIcon icon="📤" label="Export" onClick={() => setSidebarCollapsed(false)} />
          </div>
        )}
      </aside>

      {/* CENTER EDITOR */}
      <main className="flex-1 overflow-y-auto min-w-0">
        <div className="max-w-3xl mx-auto p-6">{editor}</div>
      </main>

      {/* RIGHT PREVIEW */}
      <aside
        className={`border-l border-zinc-800 transition-all duration-200 flex-shrink-0 overflow-y-auto ${
          previewCollapsed ? "w-10" : "w-96"
        }`}
      >
        <div className="sticky top-0 z-10 bg-zinc-950 border-b border-zinc-800 px-2 py-2 flex items-center">
          <button
            onClick={() => setPreviewCollapsed(!previewCollapsed)}
            className="text-zinc-500 hover:text-zinc-300 p-1 rounded transition-colors"
            title={previewCollapsed ? "Show preview" : "Hide preview"}
          >
            {previewCollapsed ? "◀" : "▶"}
          </button>
          {!previewCollapsed && (
            <span className="text-xs text-zinc-500 ml-2 font-medium">Preview</span>
          )}
        </div>
        {!previewCollapsed && <div className="p-3">{preview}</div>}
      </aside>
    </div>
  );
}

function SidebarIcon({
  icon,
  label,
  onClick,
}: {
  icon: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-zinc-800 transition-colors text-base"
    >
      {icon}
    </button>
  );
}

function MobileTab({
  icon,
  label,
  active,
  onClick,
}: {
  icon: string;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 text-xs transition-colors ${
        active
          ? "text-blue-400 border-t-2 border-blue-500"
          : "text-zinc-500 border-t-2 border-transparent"
      }`}
    >
      <span className="text-base">{icon}</span>
      <span>{label}</span>
    </button>
  );
}
