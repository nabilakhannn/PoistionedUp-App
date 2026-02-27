/**
 * Core API client for PositionedUp backend.
 *
 * Handles authentication, token refresh, and error handling.
 * All domain modules import `apiFetch` from here.
 */

import { createClient } from "@/lib/supabase/client";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://poistionedup.vercel.app";

// ── Token refresh lock ──────────────────────────────────────
// Prevents concurrent requests from triggering multiple token
// refreshes simultaneously (race condition). Only the first
// caller refreshes; others wait for the same result.

let _refreshPromise: Promise<string | null> | null = null;

async function _refreshToken(): Promise<string | null> {
  // If a refresh is already in progress, wait for it
  if (_refreshPromise) {
    return _refreshPromise;
  }

  _refreshPromise = (async () => {
    try {
      const supabase = createClient();
      const { data, error } = await supabase.auth.refreshSession();
      if (error) {
        console.error("[apiFetch] Refresh failed:", error);
        await supabase.auth.signOut();
        window.location.href = "/login";
        return null;
      }
      return data.session?.access_token ?? null;
    } finally {
      // Clear the lock so future refreshes can proceed
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

// ── Main fetch wrapper ──────────────────────────────────────

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let token = "";
  if (typeof window !== "undefined") {
    const supabase = createClient();

    // getSession() triggers token refresh if expired
    const { data, error } = await supabase.auth.getSession();

    if (error) {
      console.error("[apiFetch] Session error:", error);
      const currentPath = window.location.pathname;
      if (currentPath !== "/login" && currentPath !== "/signup") {
        window.location.href = "/login";
      }
      throw new Error("Session error");
    }

    token = data.session?.access_token ?? "";

    // No session — redirect to login (unless already there)
    if (!token) {
      const currentPath = window.location.pathname;
      if (currentPath !== "/login" && currentPath !== "/signup") {
        console.warn("[apiFetch] No token, redirecting to /login");
        window.location.href = "/login";
      }
      throw new Error("Not authenticated");
    }

    // Check if token is about to expire (within 5 minutes)
    const expiresAt = data.session?.expires_at;
    if (expiresAt && expiresAt < Date.now() / 1000 + 300) {
      console.log("[apiFetch] Token expiring soon, refreshing...");
      const refreshedToken = await _refreshToken();
      if (!refreshedToken) {
        throw new Error("Session expired");
      }
      token = refreshedToken;
    }
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });
  } catch (err) {
    console.error("[apiFetch] Network error:", err);
    throw new Error(
      `Cannot reach the server. Is the backend running on port 8000?`
    );
  }

  if (res.status === 401) {
    // Token expired or invalid — sign out and redirect
    console.warn("[apiFetch] 401 Unauthorized, signing out");
    if (typeof window !== "undefined") {
      const supabase = createClient();
      await supabase.auth.signOut();
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please sign in again.");
  }

  // Handle rate limiting
  if (res.status === 429) {
    const retryAfter = res.headers.get("Retry-After") || "60";
    throw new Error(
      `Too many requests. Please wait ${retryAfter} seconds and try again.`
    );
  }

  if (!res.ok) {
    const body = await res.text();
    // Extract safe user-facing message; never expose raw server details
    let userMessage = `API error (${res.status})`;
    try {
      const json = JSON.parse(body);
      const detail = json?.error?.message || json?.detail;
      if (typeof detail === "string" && detail.length < 300) {
        userMessage = detail;
      }
    } catch {
      // body wasn't JSON — use generic message
    }
    console.error(`[apiFetch] ${res.status} on ${path}`);
    throw new Error(userMessage);
  }

  return res.json();
}
