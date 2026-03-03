"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useBrand } from "@/lib/brand-context";

const SKIP_PATHS = ["/onboarding", "/login", "/signup"];

export function OnboardingGuard() {
  const { brands, loading } = useBrand();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;
    if (SKIP_PATHS.some((p) => pathname.startsWith(p))) return;

    const done =
      typeof window !== "undefined" && localStorage.getItem("onboarding_done");
    if (!done && brands.length === 0) {
      router.replace("/onboarding");
    }
  }, [loading, brands, router, pathname]);

  return null;
}
