/**
 * OAuth / Connections API -- Google and Notion integration.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface OAuthStatus {
  connected: boolean;
  provider: string;
  scopes?: string[];
  email?: string;
}

export interface OAuthAuthURL {
  url: string;
  provider: string;
}

// ── API Methods ──────────────────────────────────────────

export const oauthApi = {
  googleAuthUrl: () => apiFetch<OAuthAuthURL>("/oauth/google/auth-url"),

  googleCallback: (code: string) =>
    apiFetch<{ message: string; provider: string }>(
      "/oauth/google/callback",
      {
        method: "POST",
        body: JSON.stringify({ code }),
      }
    ),

  googleStatus: () => apiFetch<OAuthStatus>("/oauth/google/status"),

  googleDisconnect: () =>
    apiFetch<{ message: string; provider: string }>(
      "/oauth/google/disconnect",
      { method: "DELETE" }
    ),

  notionAuthUrl: () => apiFetch<OAuthAuthURL>("/oauth/notion/auth-url"),

  notionCallback: (code: string) =>
    apiFetch<{
      message: string;
      provider: string;
      workspace_name?: string;
    }>("/oauth/notion/callback", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  notionStatus: () => apiFetch<OAuthStatus>("/oauth/notion/status"),

  notionDisconnect: () =>
    apiFetch<{ message: string; provider: string }>(
      "/oauth/notion/disconnect",
      { method: "DELETE" }
    ),
};
