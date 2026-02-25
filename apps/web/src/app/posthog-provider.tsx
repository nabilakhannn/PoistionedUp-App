"use client";

import { useEffect, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { initPostHog, trackPageView } from "@/lib/posthog";

/**
 * PostHogProvider initializes the PostHog client on mount and
 * tracks page views on every Next.js route change.
 *
 * Place this inside the <body> of layout.tsx (as a sibling, not wrapping children).
 */
export function PostHogProvider() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isFirstRender = useRef(true);

  // Initialize PostHog on mount
  useEffect(() => {
    initPostHog();
  }, []);

  // Track page views on route change
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      // Track the initial page load
      const url = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : "");
      trackPageView(url);
      return;
    }

    const url = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : "");
    trackPageView(url);
  }, [pathname, searchParams]);

  return null; // This component renders nothing
}
