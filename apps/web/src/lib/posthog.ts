/**
 * PostHog analytics client initialization.
 *
 * Reads NEXT_PUBLIC_POSTHOG_KEY and NEXT_PUBLIC_POSTHOG_HOST from environment.
 * If the key is missing, all tracking calls become no-ops.
 */
import posthog from "posthog-js";

let initialized = false;

export function initPostHog() {
  if (initialized) return;
  if (typeof window === "undefined") return;

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const host =
    process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com";

  if (!key) {
    console.warn("[PostHog] No NEXT_PUBLIC_POSTHOG_KEY set, analytics disabled");
    return;
  }

  posthog.init(key, {
    api_host: host,
    // Capture pageviews automatically via Next.js router integration
    capture_pageview: false, // We handle this manually with the router
    capture_pageleave: true,
    persistence: "localStorage+cookie",
    autocapture: true,
    // Respect Do Not Track
    respect_dnt: true,
  });

  initialized = true;
}

export function getPostHog() {
  if (!initialized) return null;
  return posthog;
}

// ── Convenience wrappers ────────────────────────────────────

/**
 * Identify a user after login/signup.
 * Sets the PostHog distinct_id and attaches user properties.
 */
export function identifyUser(
  userId: string,
  properties?: Record<string, unknown>
) {
  const ph = getPostHog();
  if (!ph) return;
  ph.identify(userId, properties);
}

/**
 * Reset the PostHog identity on logout.
 */
export function resetUser() {
  const ph = getPostHog();
  if (!ph) return;
  ph.reset();
}

/**
 * Track a custom event.
 */
export function trackEvent(
  eventName: string,
  properties?: Record<string, unknown>
) {
  const ph = getPostHog();
  if (!ph) return;
  ph.capture(eventName, properties);
}

/**
 * Track a page view (called from the PostHogProvider on route change).
 */
export function trackPageView(url: string) {
  const ph = getPostHog();
  if (!ph) return;
  ph.capture("$pageview", { $current_url: url });
}
