"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useBrand } from "@/lib/brand-context";
import { NotificationBell } from "@/app/mission-control/components/notification-bell";
import { pipelineSettingsApi } from "@/lib/api/pipeline-settings";

/* ── Icon components ─────────────────────────────────── */

function DashboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z" />
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

function BrandIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5zm6-10.125a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0zm1.294 6.336a6.721 6.721 0 0 1-3.17.789 6.721 6.721 0 0 1-3.168-.789 3.376 3.376 0 0 1 6.338 0z" />
    </svg>
  );
}

function GrowthIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.28m5.94 2.28-2.28 5.941" />
    </svg>
  );
}

function JumboIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
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
      fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
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

/* ── 4 Rooms + Jumbo ────────────────────────────────── */

const PRIMARY_NAV = [
  {
    href: "/dashboard",
    label: "Dashboard",
    subtitle: "Approvals & activity",
    icon: DashboardIcon,
    match: (p: string) => p === "/dashboard" || p.startsWith("/dashboard/"),
  },
  {
    href: "/content",
    label: "Content",
    subtitle: "Create & plan",
    icon: ContentIcon,
    match: (p: string) => p === "/content" || p.startsWith("/content/"),
  },
  {
    href: "/brand",
    label: "Brand",
    subtitle: "Research & profile",
    icon: BrandIcon,
    match: (p: string) => p === "/brand" || p.startsWith("/brand/") || p.startsWith("/brands"),
  },
  {
    href: "/growth",
    label: "Growth",
    subtitle: "Leads & outreach",
    icon: GrowthIcon,
    match: (p: string) => p === "/growth" || p.startsWith("/growth/"),
  },
];

/* ── NavBar ──────────────────────────────────────────── */

export function NavBar() {
  const router = useRouter();
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [brandDropdownOpen, setBrandDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { brands, currentBrand, selectBrand, loading: brandsLoading } = useBrand();
  const [approvalCount, setApprovalCount] = useState(0);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }: any) => {
      setLoggedIn(!!data.session);
    }).catch(() => setLoggedIn(false));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: any, session: any) => {
      setLoggedIn(!!session);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // Poll approval count every 60s
  useEffect(() => {
    const fetchCount = () => {
      pipelineSettingsApi.getApprovalsCount()
        .then((r) => setApprovalCount(r.count))
        .catch(() => {/* silent */});
    };
    fetchCount();
    const id = setInterval(fetchCount, 60_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setBrandDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (pathname === "/login" || pathname === "/signup" || pathname === "/onboarding") return null;
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

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="px-4 pt-6 pb-4">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="font-semibold text-zinc-100 text-lg tracking-tight">PositionedUp</span>
        </Link>
      </div>

      {/* Brand selector */}
      {!brandsLoading && brands.length > 0 && (
        <div ref={dropdownRef} className="px-3 mb-4 relative">
          <button
            onClick={() => setBrandDropdownOpen(!brandDropdownOpen)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/[0.03] ring-1 ring-white/[0.06] hover:bg-white/[0.06] text-sm font-medium text-zinc-300 transition-colors duration-200"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
            <span className="flex-1 text-left truncate">
              {currentBrand ? currentBrand.name : "Select brand"}
            </span>
            <ChevronIcon className="w-3.5 h-3.5 text-zinc-500" open={brandDropdownOpen} />
          </button>

          {brandDropdownOpen && (
            <div className="absolute left-3 right-3 top-full mt-1 bg-zinc-900 ring-1 ring-white/[0.08] rounded-xl shadow-2xl z-50 py-1 animate-fade-in">
              {brands.map((brand) => (
                <button
                  key={brand.id}
                  onClick={() => handleBrandSwitch(brand.id)}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors duration-150 ${
                    currentBrand?.id === brand.id
                      ? "bg-violet-500/15 text-violet-300 font-medium"
                      : "text-zinc-300 hover:bg-white/[0.04]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate">{brand.name}</span>
                    {currentBrand?.id === brand.id && (
                      <svg className="w-4 h-4 text-violet-400 flex-shrink-0 ml-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  {brand.description && (
                    <p className="text-xs text-zinc-500 truncate mt-0.5">{brand.description}</p>
                  )}
                </button>
              ))}
              <div className="border-t border-white/[0.06] mt-1 pt-1">
                <Link
                  href="/brands/new"
                  onClick={() => setBrandDropdownOpen(false)}
                  className="block px-3 py-2 text-sm text-violet-400 hover:bg-white/[0.04] transition-colors duration-150"
                >
                  + New Brand
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Primary Rooms */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {PRIMARY_NAV.map((item) => {
          const Icon = item.icon;
          const active = item.match(pathname || "");
          const isDashboardBadge = item.href === "/dashboard" && approvalCount > 0;
          return (
            <Link
              key={item.href}
              href={item.href}
              data-testid={`nav-${item.label.toLowerCase()}`}
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                active
                  ? "bg-white/[0.06] ring-1 ring-white/[0.08] text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.03]"
              }`}
            >
              <Icon className={`w-[18px] h-[18px] flex-shrink-0 ${active ? "text-violet-400" : "text-zinc-600 group-hover:text-zinc-400"}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-medium">{item.label}</span>
                  {isDashboardBadge && (
                    <span className="text-[10px] font-semibold bg-violet-500 text-white rounded-full px-1.5 py-0.5 leading-none">
                      {approvalCount}
                    </span>
                  )}
                </div>
                <span className={`text-[11px] leading-tight ${active ? "text-zinc-500" : "text-zinc-600"}`}>
                  {item.subtitle}
                </span>
              </div>
            </Link>
          );
        })}

        {/* Jumbo — special accent link */}
        <div className="pt-2">
          <Link
            href="/jumbo"
            data-testid="nav-jumbo"
            className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
              pathname?.startsWith("/jumbo") || pathname?.startsWith("/intelligence")
                ? "bg-gradient-to-r from-violet-500/10 to-blue-500/10 ring-1 ring-violet-500/20 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.03]"
            }`}
          >
            <JumboIcon className={`w-[18px] h-[18px] flex-shrink-0 ${
              pathname?.startsWith("/jumbo") || pathname?.startsWith("/intelligence") ? "text-violet-400" : "text-zinc-600 group-hover:text-violet-400"
            }`} />
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium">Jumbo</span>
              <span className={`block text-[11px] leading-tight ${
                pathname?.startsWith("/jumbo") || pathname?.startsWith("/intelligence") ? "text-zinc-500" : "text-zinc-600"
              }`}>Chat & notes</span>
            </div>
          </Link>
        </div>
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-4 mt-auto border-t border-white/[0.06] pt-3 space-y-0.5">
        <Link
          href="/brand?tab=settings"
          className={`flex items-center gap-3 w-full px-3 py-2 rounded-xl text-sm font-medium transition-colors duration-200 ${
            pathname === "/brand" && typeof window !== "undefined" && window.location.search.includes("tab=settings")
              ? "text-violet-400"
              : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.03]"
          }`}
        >
          <SettingsIcon className="w-[18px] h-[18px]" />
          Settings
        </Link>
        <div className="flex items-center gap-3 px-3 py-2">
          <NotificationBell />
          <span className="text-sm text-zinc-500">Notifications</span>
        </div>
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-sm font-medium text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.03] transition-colors duration-200"
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
      <aside className="hidden md:flex md:flex-col md:fixed md:inset-y-0 md:left-0 md:w-60 bg-[#09090B]/80 backdrop-blur-md border-r border-white/[0.06] z-40">
        {sidebarContent}
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-14 bg-[#09090B]/90 backdrop-blur-md border-b border-white/[0.06] flex items-center justify-between px-4 z-40">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
            <span className="text-white font-bold text-xs">P</span>
          </div>
          <span className="font-semibold text-zinc-100 text-base">PositionedUp</span>
        </Link>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.06]"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <CloseIcon className="w-5 h-5" /> : <MenuIcon className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <>
          <div className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={() => setMobileOpen(false)} />
          <aside className="md:hidden fixed inset-y-0 left-0 w-64 bg-[#09090B] border-r border-white/[0.06] z-50 flex flex-col overflow-y-auto animate-slide-up">
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  );
}
