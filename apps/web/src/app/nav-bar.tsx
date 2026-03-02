"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useBrand } from "@/lib/brand-context";
import { NotificationBell } from "@/app/mission-control/components/notification-bell";

/* ── Icon components ─────────────────────────────────── */

function BrandsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
    </svg>
  );
}

function KnowledgeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
    </svg>
  );
}

function InspoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
    </svg>
  );
}

function ContentIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
    </svg>
  );
}

function AdCreativeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  );
}

function ComposerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
    </svg>
  );
}

function ScheduleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
    </svg>
  );
}

function PerformanceIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
    </svg>
  );
}

function ResearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  );
}

function UsageIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Z" />
    </svg>
  );
}

function StrategistIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
    </svg>
  );
}

function MissionControlIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a9 9 0 1 1-18 0V5.25" />
    </svg>
  );
}

function AdminIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
    </svg>
  );
}

function LogOutIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
    </svg>
  );
}

function ChevronIcon({ className, open }: { className?: string; open: boolean }) {
  return (
    <svg
      className={`${className} transition-transform duration-200 ${open ? "rotate-180" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

/* ── NavBar (sidebar) ────────────────────────────────── */

export function NavBar() {
  const router = useRouter();
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [brandDropdownOpen, setBrandDropdownOpen] = useState(false);
  const [mcExpanded, setMcExpanded] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { brands, currentBrand, selectBrand, loading: brandsLoading } = useBrand();

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }: any) => {
      setLoggedIn(!!data.session);
    }).catch(() => setLoggedIn(false));

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event: any, session: any) => {
      setLoggedIn(!!session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Close mobile menu on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Auto-expand Mission Control section when on MC pages
  useEffect(() => {
    if (pathname?.startsWith("/mission-control")) {
      setMcExpanded(true);
    }
  }, [pathname]);

  // Close brand dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setBrandDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Hide nav on login/signup pages
  if (pathname === "/login" || pathname === "/signup") {
    return null;
  }

  if (!loggedIn) return null;

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  };

  const handleBrandSwitch = (brandId: string) => {
    selectBrand(brandId);
    setBrandDropdownOpen(false);
  };

  const navLinks = [
    { href: "/brands", label: "Brands", icon: BrandsIcon },
    // Dynamic strategist link: only shown when a brand is selected
    ...(currentBrand
      ? [{ href: `/brands/${currentBrand.id}/strategist`, label: "Strategist", icon: StrategistIcon }]
      : []),
    { href: "/knowledge", label: "Knowledge", icon: KnowledgeIcon },
    { href: "/inspo", label: "Inspo", icon: InspoIcon },
    { href: "/content", label: "Content", icon: ContentIcon },
    { href: "/composer", label: "Composer", icon: ComposerIcon },
    { href: "/ad-creative", label: "Ad Creative", icon: AdCreativeIcon },
    { href: "/research", label: "Research", icon: ResearchIcon },
    { href: "/schedule", label: "Schedule", icon: ScheduleIcon },
    { href: "/performance", label: "Performance", icon: PerformanceIcon },
    { href: "/usage", label: "Usage", icon: UsageIcon },
  ];

  const mcSubLinks = [
    { href: "/mission-control", label: "Dashboard" },
    { href: "/mission-control/analytics", label: "Analytics" },
    { href: "/mission-control/orchestrator", label: "Orchestrator" },
    { href: "/mission-control/gateway", label: "Gateway" },
    { href: "/mission-control/chat", label: "Agent Chat" },
    { href: "/mission-control/goals", label: "Goals" },
    { href: "/mission-control/competitors", label: "Competitors" },
    { href: "/mission-control/qa", label: "QA" },
  ];

  const adminLinks = [
    { href: "/admin/training", label: "Agent Training", icon: AdminIcon },
  ];

  const isActive = (href: string) =>
    pathname === href || pathname?.startsWith(href + "/");

  /* ── Sidebar content (shared between desktop and mobile) ── */
  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="px-4 pt-6 pb-4">
        <Link href="/brands" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">P</span>
          </div>
          <span className="font-semibold text-card-foreground text-lg tracking-tight">PositionedUp</span>
        </Link>
      </div>

      {/* Brand selector */}
      {!brandsLoading && brands.length > 0 && (
        <div ref={dropdownRef} className="px-3 mb-4 relative">
          <button
            onClick={() => setBrandDropdownOpen(!brandDropdownOpen)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border bg-sidebar-accent/50 hover:bg-sidebar-accent text-sm font-medium text-sidebar-foreground transition"
          >
            <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
            <span className="flex-1 text-left truncate">
              {currentBrand ? currentBrand.name : "Select brand"}
            </span>
            <ChevronIcon className="w-3.5 h-3.5 text-muted-foreground" open={brandDropdownOpen} />
          </button>

          {brandDropdownOpen && (
            <div className="absolute left-3 right-3 top-full mt-1 bg-popover border border-border rounded-lg shadow-xl z-50 py-1">
              {brands.map((brand) => (
                <button
                  key={brand.id}
                  onClick={() => handleBrandSwitch(brand.id)}
                  className={`w-full text-left px-3 py-2 text-sm transition ${
                    currentBrand?.id === brand.id
                      ? "bg-primary/20 text-primary font-medium"
                      : "text-popover-foreground hover:bg-sidebar-accent"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate">{brand.name}</span>
                    {currentBrand?.id === brand.id && (
                      <svg className="w-4 h-4 text-primary flex-shrink-0 ml-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  {brand.description && (
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{brand.description}</p>
                  )}
                </button>
              ))}
              <div className="border-t border-border mt-1 pt-1">
                <Link
                  href="/brands/new"
                  onClick={() => setBrandDropdownOpen(false)}
                  className="block px-3 py-2 text-sm text-primary hover:bg-sidebar-accent transition"
                >
                  + New Brand
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Nav links */}
      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
        <p className="px-3 mb-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          Navigation
        </p>
        {navLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-primary/15 text-primary border border-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent border border-transparent"
              }`}
            >
              <Icon className={`w-[18px] h-[18px] flex-shrink-0 ${active ? "text-primary" : "text-muted-foreground"}`} />
              {link.label}
            </Link>
          );
        })}

        {/* Mission Control (expandable) */}
        <div>
          <button
            onClick={() => setMcExpanded(!mcExpanded)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              pathname?.startsWith("/mission-control")
                ? "bg-primary/15 text-primary border border-primary/20"
                : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent border border-transparent"
            }`}
          >
            <MissionControlIcon className={`w-[18px] h-[18px] flex-shrink-0 ${pathname?.startsWith("/mission-control") ? "text-primary" : "text-muted-foreground"}`} />
            <span className="flex-1 text-left">Mission Control</span>
            <ChevronIcon className="w-3.5 h-3.5 text-muted-foreground" open={mcExpanded} />
          </button>
          {mcExpanded && (
            <div className="ml-7 mt-0.5 space-y-0.5">
              {mcSubLinks.map((sub) => {
                const subActive = pathname === sub.href;
                return (
                  <Link
                    key={sub.href}
                    href={sub.href}
                    className={`block px-3 py-1.5 rounded-md text-[13px] transition-colors ${
                      subActive
                        ? "text-primary font-medium bg-primary/10"
                        : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
                    }`}
                  >
                    {sub.label}
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Admin section */}
        <div className="pt-4 mt-4 border-t border-sidebar-border">
          <p className="px-3 mb-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            Admin
          </p>
          {adminLinks.map((link) => {
            const Icon = link.icon;
            const active = isActive(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "bg-primary/15 text-primary border border-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent border border-transparent"
                }`}
              >
                <Icon className={`w-[18px] h-[18px] flex-shrink-0 ${active ? "text-primary" : "text-muted-foreground"}`} />
                {link.label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Bottom section */}
      <div className="px-3 pb-4 mt-auto border-t border-sidebar-border pt-3 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2">
          <NotificationBell />
          <span className="text-sm text-muted-foreground">Notifications</span>
        </div>
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
        >
          <LogOutIcon className="w-[18px] h-[18px]" />
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:flex-col md:fixed md:inset-y-0 md:left-0 md:w-60 bg-sidebar border-r border-sidebar-border z-40">
        {sidebarContent}
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-14 bg-sidebar border-b border-sidebar-border flex items-center justify-between px-4 z-40">
        <Link href="/brands" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-xs">P</span>
          </div>
          <span className="font-semibold text-card-foreground text-base">PositionedUp</span>
        </Link>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <CloseIcon className="w-5 h-5" /> : <MenuIcon className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile overlay + drawer */}
      {mobileOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 bg-black/60 z-40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="md:hidden fixed inset-y-0 left-0 w-64 bg-sidebar border-r border-sidebar-border z-50 flex flex-col overflow-y-auto">
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  );
}
