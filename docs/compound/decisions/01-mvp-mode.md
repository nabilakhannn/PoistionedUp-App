# ADR-01: Export-Only Mode for MVP (No YouTube API Publishing)

**Status:** ACCEPTED
**Date:** 2026-02-12
**Decision maker:** Product owner
**PRD reference:** Section FR11 (Export/copy) and FR12 (Publishing)

---

## Decision

The MVP ships with **export-only** content delivery. No YouTube Data API integration, no OAuth flows, no automated publishing. Users export their Content Pack as downloadable files or copy to clipboard.

---

## Why

Publishing to YouTube would require:
1. Google OAuth 2.0 consent flow (per-user)
2. YouTube Data API v3 quotas (10,000 units/day; video upload = 1,600 units)
3. Metadata upload API integration
4. Google app verification process (takes weeks)
5. Rate limiting, error handling, quota monitoring
6. OAuth token storage, rotation, and security

**None of this helps validate the core hypothesis:** "Does the research-to-script pipeline produce content creators actually approve and use?"

Publishing adds 3-4 weeks of work to a feature that isn't the product's differentiator. The product differentiates on *research quality + script quality + deterministic pipeline + memory*. Export is sufficient to test all of this.

---

## What We Build Instead

### Copy to clipboard
- One-click copy for any individual asset (long script, shorts, titles, description, tags, pinned comment, thumbnail brief)
- Toast notification confirms copy

### Export to Google Docs
- One-click "Send to Google Docs" creates a formatted Google Doc with the full Content Pack
- Organized with headings: Long Script, Shorts 1-3, Titles, Description, Tags, etc.
- Requires Google OAuth (lightweight -- just Google Docs API scope, not YouTube)
- Doc is created in the user's Google Drive

### Export to Notion
- One-click "Send to Notion" creates a Notion page with the full Content Pack
- Uses Notion API integration (user connects once via Notion OAuth)
- Page is created in a user-selected Notion workspace/database

### Copy to clipboard (always available)
- Works without any OAuth -- instant copy of any individual asset
- Fallback if user doesn't want to connect Google or Notion

### Version history
All prior versions of assets are preserved and individually exportable.

---

## What We Defer

| Feature | Why Deferred | When |
|---------|-------------|------|
| YouTube Data API publishing | Not core to validation; high cost | v1.1+ |
| Scheduled publishing | Depends on publishing | v2+ |
| Multi-platform publishing (Instagram, TikTok) | Out of MVP scope entirely | v2+ |

**Note:** Google OAuth IS in MVP scope (for Google Docs export). Notion OAuth IS in MVP scope (for Notion export). These are lightweight integrations compared to YouTube publishing.

---

## Architecture Impact

### What this removes from the architecture:
- No YouTube API client code in `apps/api/`
- No `publish` step in the LangGraph pipeline (pipeline ends at approval)
- No YouTube API quota monitoring

### What we DO build for export:
- **Google OAuth** (lightweight: only `drive.file` + `docs` scopes -- NOT full YouTube access)
- **Notion OAuth** (single integration scope)
- `oauth_tokens` table for storing Google + Notion tokens
- Export routes: `POST /workflows/{id}/export/google-docs`, `POST /workflows/{id}/export/notion`
- Copy to clipboard (no OAuth needed -- always works)

### How export works technically:
- Google Docs: Backend creates a formatted doc via Google Docs API, returns the doc URL
- Notion: Backend creates a page via Notion API, returns the page URL
- Clipboard: Frontend copies asset content directly (no server call)

---

## Reversibility

This decision is **fully reversible**. Publishing is an additive feature that requires zero refactoring:

1. Add `oauth_tokens` table (new migration)
2. Add YouTube API client (`apps/api/integrations/youtube.py`)
3. Add `publish` node to LangGraph pipeline (after approval)
4. Add OAuth routes to the API
5. Add "Publish" button to the dashboard (gated behind OAuth connection)

No existing code changes. Clean extension point.
