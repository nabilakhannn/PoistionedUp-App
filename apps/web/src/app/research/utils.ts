/* ────────────────────────────────────────────────────────
   Research Feed: Utility Functions
   ──────────────────────────────────────────────────────── */

import { ResearchResult, ResearchResponse } from "@/lib/api";
import { FeedCard, Platform } from "./constants";

/* ── Extract author from title/URL ── */

export function extractAuthor(result: ResearchResult, source: string): string {
  if (result.publisher) return result.publisher;

  const url = result.url || "";

  if (source === "linkedin") {
    const match = url.match(/linkedin\.com\/(?:in|posts)\/([^/?]+)/);
    if (match) return `@${match[1].replace(/-/g, " ")}`;
  }

  if (source === "reddit") {
    const match = url.match(/reddit\.com\/r\/([^/?]+)/);
    if (match) return `r/${match[1]}`;
    const userMatch = url.match(/reddit\.com\/user\/([^/?]+)/);
    if (userMatch) return `u/${userMatch[1]}`;
  }

  if (source === "youtube") {
    return result.publisher || "YouTube Creator";
  }

  if (source === "tiktok") {
    const match = url.match(/tiktok\.com\/@([^/?]+)/);
    if (match) return `@${match[1]}`;
  }

  try {
    const domain = new URL(url).hostname.replace("www.", "");
    return domain;
  } catch {
    return source;
  }
}

export function extractDate(): string {
  const now = new Date();
  return `${now.getMonth() + 1}/${now.getDate()}/${now.getFullYear()}`;
}

/* ── Transform API results to FeedCards ── */

export function transformToFeedCards(response: ResearchResponse): FeedCard[] {
  const cards: FeedCard[] = [];

  for (const r of response.web_results || []) {
    cards.push({
      id: `web-${r.url}-${Math.random()}`,
      title: r.title,
      snippet: r.snippet || r.description || "",
      url: r.url,
      source: (r.source as Platform) || "all",
      author: extractAuthor(r, r.source || "web"),
      date: extractDate(),
      views: r.views || "",
      likes: "",
      comments: "",
      shares: "",
    });
  }

  for (const r of response.youtube_trends || []) {
    cards.push({
      id: `yt-${r.url}-${Math.random()}`,
      title: r.title,
      snippet: r.description || r.snippet || "",
      url: r.url,
      source: "youtube",
      author: r.publisher || extractAuthor(r, "youtube"),
      date: extractDate(),
      views: r.views || "",
      likes: "",
      comments: "",
      shares: "",
    });
  }

  for (const r of response.reddit_discussions || []) {
    cards.push({
      id: `reddit-${r.url}-${Math.random()}`,
      title: r.title,
      snippet: r.snippet || "",
      url: r.url,
      source: "reddit",
      author: extractAuthor(r, "reddit"),
      date: extractDate(),
      views: "",
      likes: "",
      comments: "",
      shares: "",
    });
  }

  return cards;
}
