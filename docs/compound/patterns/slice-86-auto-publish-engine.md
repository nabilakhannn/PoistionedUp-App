# Slice 86 — Auto-Publish Engine: Close the Last Gap

**Date:** 2026-03-02
**Status:** Complete
**Tests:** 1261 total (+30) | 30/30 slice tests pass | 0 TS errors

---

## The Problem Solved

Content was being created, written, QA'd, approved, staged to Composer, and scheduled —
but nothing ever actually posted. `scheduled_items` rows with `status='scheduled'` and
a `scheduled_at` timestamp just sat in the database forever. Connectors (Slice 85) stored
encrypted social credentials but zero code used them.

**Slice 86 closes this gap:** the entire workflow now terminates in a live post.

---

## What Was Built

1. **Publishing service** (`app/services/publishing.py`) — routes content to platform publishers
2. **Publishing router** (`app/routers/publishing.py`) — 3 JWT-protected endpoints
3. **"Publish Now" button** in Composer — appears when a connector exists for the platform
4. **"Run Due Posts" endpoint** — batch-publishes all overdue scheduled items
5. **Twitter/X OAuth 1.0a upgrade** — updated connector from read-only bearer_token to 4-field OAuth that can actually post
6. **LinkedIn webhook guidance** — updated connector UI to route through Make.com/Zapier (safe, official)
7. **Database migration 031** — adds `publish_error` + `publish_attempted_at` columns + partial index

---

## Architecture

```
Composer / Scheduler
  └── "Publish Now" → POST /schedule/{id}/publish
                              ↓
                     publishing.py:publish_item()
                              ↓
                   load item → find connector → decrypt creds
                              ↓
           ┌──────────────────────────────────────────┐
           │ twitter   → _post_twitter() (tweepy)     │
           │ webhook / │                              │
           │ linkedin  → _post_webhook() (HMAC-signed)│
           │ instagram → _post_instagram() (2-step)   │
           └──────────────────────────────────────────┘
                              ↓
              DB update: status=published, published_at, published_url
```

---

## Platform Details

### Twitter/X — OAuth 1.0a (not bearer token)
**Why the change:** bearer tokens are READ-ONLY on Twitter API v2. Posting requires OAuth 1.0a.
**New credential shape:** `api_key`, `api_secret`, `access_token`, `access_token_secret`
**Library:** `tweepy>=4.14.0` — `client.create_tweet(text=body[:280])`
**URL:** `https://twitter.com/{username}/status/{tweet_id}`
**Error handling:** TooManyRequests → "rate limit" message, Unauthorized → "invalid/expired" message

### Webhook — Universal Bridge (Make.com, Zapier, Buffer)
**Payload:**
```json
{"event": "content.publish", "platform": "linkedin", "title": "...", "body": "...",
 "scheduled_at": "ISO", "brand_id": "uuid", "item_id": "uuid"}
```
**Signing:** `X-Signature: sha256=HMAC(secret, payload_bytes)` — only if secret is set
**LinkedIn guidance:** connector card updated to explain Make.com/Zapier workflow
**Why not direct LinkedIn:** li_at session cookies violate ToS and expire every ~30 days

### Instagram — Two-Step Graph API
1. `POST /{page_id}/media` with `caption` → get `creation_id`
2. `POST /{page_id}/media_publish` with `creation_id` → get post `id`
**URL:** `https://www.instagram.com/p/{post_id}/`
**Requires:** Facebook Business + Instagram Business/Creator account linked

---

## Key Code Patterns

### Publish Item — Ownership + Error Safety
```python
def publish_item(item_id: str, user_id: str, sb) -> PublishResult:
    # 1. Load item with user_id equality check (ownership enforced at DB level)
    # 2. Map platform to connector service (linkedin → webhook)
    # 3. Decrypt credentials from user_connectors
    # 4. Route to platform fn
    # 5. Write publish_error on failure (never change status)
    # 6. Write published_at + published_url on success
```

### Run Due Posts — Batch with Safety Cap
```python
def run_due_posts(user_id: str, sb) -> RunDueResult:
    # Query: status='scheduled' AND scheduled_at <= NOW()
    # LIMIT 50 — safety cap prevents runaway processing
    # Failed items keep status='scheduled' → retry on next call
```

### HMAC Signing for Webhooks
```python
import hmac, hashlib
sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
headers["X-Signature"] = f"sha256={sig}"
```

### SSRF Protection — Double Validated
```python
validate_url(url)  # called on save (connectors.py) AND on publish (publishing.py)
```

---

## Frontend Changes

**Composer — "Publish Now" button:**
- Appears only when `draftId` is set AND platform has a connected connector
- LinkedIn maps to webhook connector check
- On success: shows live post link + "View live post" anchor
- On failure: shows error in existing error banner

**Settings — Twitter updated:**
- 4 input fields: API Key, API Secret, Access Token, Access Token Secret
- Label guidance: "Get keys from developer.twitter.com → Your App → Keys and Tokens"

**Settings — LinkedIn updated:**
- Label: "LinkedIn (via Webhook)"
- Placeholder changed to `https://hook.make.com/...`
- Description explains Make.com/Zapier route

---

## Security Checklist

| Risk | Mitigation |
|------|-----------|
| SSRF via webhook | `validate_url_for_fetch()` called at publish time (double-check) |
| Credential leak in error | All platform exceptions caught; safe strings returned |
| Wrong user's item | `eq("user_id", user_id)` on DB query; returns 404 if not found |
| Twitter rate limit | TooManyRequests → HTTP 429-friendly error |
| Webhook HMAC forgery | Signed with `hmac.new(secret, payload, sha256)` |

---

## Files Changed

### New Files (4)
| File | Purpose |
|------|---------|
| `infra/supabase/migrations/031_publishing.sql` | publish_error + partial index |
| `apps/api/app/services/publishing.py` | Publishing service (Twitter, Webhook, Instagram) |
| `apps/api/app/routers/publishing.py` | 3 publish endpoints |
| `apps/web/src/lib/api/publishing.ts` | Publishing API client |
| `apps/api/tests/test_slice86.py` | 30 new tests |

### Modified Files (7)
| File | Change |
|------|--------|
| `apps/api/app/main.py` | Register publishing router |
| `apps/api/app/services/connectors.py` | Twitter credential shape → OAuth 1.0a |
| `apps/web/src/app/mission-control/settings/page.tsx` | Updated Twitter + LinkedIn cards |
| `apps/web/src/app/composer/page.tsx` | "Publish Now" button + publishingApi import |
| `apps/api/requirements.txt` | `tweepy>=4.14.0` |
| `apps/api/requirements-full.txt` | `tweepy>=4.14.0` |
| `apps/api/tests/test_slice85.py` | Updated Twitter credential test (Slice 86 changed shape) |

---

## Test Results

| Group | Tests | Result |
|-------|-------|--------|
| TestPublishResult | 2 | ✅ pass |
| TestRunDueResult | 2 | ✅ pass |
| TestBodyExtraction | 3 | ✅ pass |
| TestTwitterPublisher | 5 | ✅ pass |
| TestWebhookPublisher | 5 | ✅ pass |
| TestInstagramPublisher | 3 | ✅ pass |
| TestPublishItem | 3 | ✅ pass |
| TestRunDuePosts | 2 | ✅ pass |
| TestConnectorTwitterShape | 3 | ✅ pass |
| TestRequiredFields | 2 | ✅ pass |
| **Total** | **30** | **30/30 passed** |

Full suite: **1233/1261 passing** (28 = pre-existing `test_resources.py` httpx.ReadTimeout).

---

## Pending (post-deploy)

1. Run migration `031_publishing.sql` in Supabase dashboard
2. Add Twitter API credentials in Settings → Twitter/X (4 OAuth fields)
3. For LinkedIn: set up Make.com webhook scenario → paste URL in Settings → LinkedIn
4. For Instagram: ensure Facebook Business + Instagram Business account linked

---

## Bugs Fixed During Implementation

1. **Python 3.9 `str | None` syntax** — `str | None` is Python 3.10+ only; fixed to `Optional[str]` with `from __future__ import annotations`
2. **Wrong auth import** — publishing router used `app.deps` for `get_current_user`; actual location is `app.auth`
3. **Wrong patch path** — webhook tests patched `app.utils.url_validation.validate_url_for_fetch` but should patch `app.services.publishing.validate_url` (the bound alias)
4. **Slice 85 test broken by credential shape change** — Twitter `bearer_token` test updated to match new OAuth 1.0a shape
