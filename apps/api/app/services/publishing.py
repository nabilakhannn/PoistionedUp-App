"""Publishing service — Slice 86.

Closes the last-mile gap: takes a scheduled_item and actually posts it
to the configured social platform using the user's stored connector credentials.

Supported platforms:
  twitter   — Twitter/X via OAuth 1.0a (tweepy)
  webhook   — Universal HMAC-signed webhook (Make.com, Zapier, Buffer, etc.)
  linkedin  — Routed through webhook (LinkedIn official API requires partner approval;
               li_at unofficial approach is against ToS and expires constantly)
  instagram — Two-step Graph API (create container → publish)

Usage:
    result = publish_item(item_id="uuid", user_id="uuid", sb=supabase_client)
    if result.success:
        print(f"Posted: {result.published_url}")
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.utils.url_validation import validate_url_for_fetch as validate_url

logger = logging.getLogger("app.services.publishing")


# ── Result type ───────────────────────────────────────────────────────────


@dataclass
class PublishResult:
    """Result of a single publish attempt."""
    success: bool
    item_id: str
    platform: str
    published_url: Optional[str] = None
    published_at: Optional[str] = None  # ISO string
    error: Optional[str] = None


@dataclass
class RunDueResult:
    """Aggregate result of run_due_posts()."""
    published: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)


# ── Platform publishers ───────────────────────────────────────────────────


def _post_twitter(body: str, creds: Dict[str, str]) -> str:
    """Post a tweet via Twitter API v2 with OAuth 1.0a.

    Requires credentials: api_key, api_secret, access_token, access_token_secret.
    Returns the live tweet URL on success.
    Raises RuntimeError on failure (message is safe — no raw credentials).
    """
    try:
        import tweepy  # noqa: PLC0415
    except ImportError:
        raise RuntimeError("tweepy not installed — add tweepy>=4.14.0 to requirements.txt")

    required = ["api_key", "api_secret", "access_token", "access_token_secret"]
    missing = [f for f in required if not creds.get(f, "").strip()]
    if missing:
        raise RuntimeError(f"Twitter connector missing fields: {missing}. Please update credentials in Settings.")

    try:
        client = tweepy.Client(
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            access_token=creds["access_token"],
            access_token_secret=creds["access_token_secret"],
        )
        # Truncate to 280 chars — Twitter's hard limit
        tweet_text = body[:280]
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]

        # Fetch username for URL construction
        try:
            me = client.get_me()
            username = me.data.username
            url = f"https://twitter.com/{username}/status/{tweet_id}"
        except Exception:
            # Fallback URL format if username lookup fails
            url = f"https://twitter.com/i/web/status/{tweet_id}"

        return url

    except tweepy.TooManyRequests:
        raise RuntimeError("Twitter rate limit exceeded — try again in 15 minutes")
    except tweepy.Unauthorized:
        raise RuntimeError("Twitter credentials are invalid or expired — please update in Settings")
    except tweepy.Forbidden:
        raise RuntimeError("Twitter token lacks write permissions — ensure app has Read+Write access")
    except Exception as exc:
        # Safe error — never include raw credentials in message
        safe_msg = str(exc)[:200]
        if any(k in safe_msg for k in (creds.get("api_key", ""), creds.get("access_token", ""))):
            safe_msg = "Twitter API call failed (details redacted)"
        raise RuntimeError(f"Twitter post failed: {safe_msg}")


def _post_webhook(item: Dict[str, Any], creds: Dict[str, str]) -> str:
    """POST content to a webhook URL with optional HMAC-SHA256 signing.

    Payload shape:
        {
            "event": "content.publish",
            "platform": "linkedin",
            "title": "...",
            "body": "...",
            "scheduled_at": "ISO timestamp",
            "brand_id": "uuid"
        }

    Adds X-Signature header if 'secret' is configured.
    Returns the webhook URL as the published_url (there's no post URL from webhooks).
    Raises RuntimeError if SSRF check fails or webhook returns 4xx/5xx.
    """
    url = creds.get("url", "").strip()
    secret = creds.get("secret", "").strip()

    # SSRF protection — re-validate at publish time even if validated on save
    validate_url(url)

    payload = {
        "event": "content.publish",
        "platform": item.get("platform", ""),
        "title": item.get("title", ""),
        "body": _extract_body(item),
        "scheduled_at": item.get("scheduled_at"),
        "brand_id": item.get("brand_id"),
        "item_id": item.get("id"),
    }
    payload_bytes = json.dumps(payload).encode()

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        headers["X-Signature"] = f"sha256={sig}"

    try:
        resp = httpx.post(url, content=payload_bytes, headers=headers, timeout=15.0)
        if resp.status_code >= 400:
            raise RuntimeError(f"Webhook returned HTTP {resp.status_code}")
        return url  # No post-specific URL from webhooks; return webhook URL as reference
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError("Webhook delivery failed — check URL is reachable")


def _post_instagram(body: str, creds: Dict[str, str]) -> str:
    """Post to Instagram via two-step Graph API.

    Step 1: Create media container (POST /{page_id}/media)
    Step 2: Publish container (POST /{page_id}/media_publish)

    Returns the live post URL on success.
    """
    access_token = creds.get("access_token", "").strip()
    page_id = creds.get("page_id", "").strip()

    if not access_token or not page_id:
        raise RuntimeError("Instagram connector missing access_token or page_id — update in Settings")

    base = f"https://graph.facebook.com/v21.0/{page_id}"

    try:
        # Step 1: Create media container
        create_resp = httpx.post(
            f"{base}/media",
            params={
                "caption": body[:2200],  # Instagram caption limit
                "media_type": "TEXT",
                "access_token": access_token,
            },
            timeout=15.0,
        )
        create_data = create_resp.json()
        if create_resp.status_code != 200 or "id" not in create_data:
            err = create_data.get("error", {}).get("message", f"HTTP {create_resp.status_code}")
            if access_token in err:
                err = "Invalid or expired access token"
            raise RuntimeError(f"Instagram create container failed: {err}")

        creation_id = create_data["id"]

        # Step 2: Publish the container
        publish_resp = httpx.post(
            f"{base}/media_publish",
            params={
                "creation_id": creation_id,
                "access_token": access_token,
            },
            timeout=15.0,
        )
        publish_data = publish_resp.json()
        if publish_resp.status_code != 200 or "id" not in publish_data:
            err = publish_data.get("error", {}).get("message", f"HTTP {publish_resp.status_code}")
            raise RuntimeError(f"Instagram publish failed: {err}")

        post_id = publish_data["id"]
        return f"https://www.instagram.com/p/{post_id}/"

    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError("Instagram Graph API call failed — check access token and page ID")


def _extract_body(item: Dict[str, Any]) -> str:
    """Extract the main text body from a scheduled_item's content_json or body_preview."""
    body_preview = item.get("body_preview") or ""
    content_json = item.get("content_json") or {}

    # Try common content_json shapes
    if isinstance(content_json, dict):
        body = (
            content_json.get("body")
            or content_json.get("text")
            or content_json.get("caption")
            or content_json.get("content")
            or body_preview
        )
    else:
        body = body_preview

    return str(body).strip()


# ── Main publish entry point ──────────────────────────────────────────────


def publish_item(item_id: str, user_id: str, sb) -> PublishResult:
    """Publish a single scheduled_item immediately.

    Loads the item, finds the matching connector, decrypts credentials,
    routes to the platform publisher, then updates the item in the DB.

    Args:
        item_id: UUID of the scheduled_item to publish.
        user_id: JWT-verified user ID (ownership check).
        sb: Supabase admin client.

    Returns:
        PublishResult with success flag, published_url, and optional error.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── 1. Load item ──────────────────────────────────────────────────────
    item_resp = (
        sb.table("scheduled_items")
        .select("*")
        .eq("id", item_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not item_resp.data:
        return PublishResult(
            success=False,
            item_id=item_id,
            platform="unknown",
            error="Item not found or access denied",
        )

    item = item_resp.data[0]
    platform = item.get("platform", "").lower()

    # ── 2. Find connector ─────────────────────────────────────────────────
    # LinkedIn posts go through webhook connector
    connector_service = "webhook" if platform == "linkedin" else platform

    conn_resp = (
        sb.table("user_connectors")
        .select("encrypted_credentials")
        .eq("user_id", user_id)
        .eq("service", connector_service)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not conn_resp.data:
        error = f"No {connector_service} connector configured — add one in Settings"
        _write_publish_error(sb, item_id, error, now_iso)
        return PublishResult(success=False, item_id=item_id, platform=platform, error=error)

    # ── 3. Decrypt credentials ────────────────────────────────────────────
    from app.services.connectors import decrypt_credentials  # noqa: PLC0415
    try:
        creds = decrypt_credentials(conn_resp.data[0]["encrypted_credentials"])
    except Exception:
        error = "Failed to decrypt connector credentials — connector may be corrupt"
        _write_publish_error(sb, item_id, error, now_iso)
        return PublishResult(success=False, item_id=item_id, platform=platform, error=error)

    # ── 4. Route to platform publisher ───────────────────────────────────
    body = _extract_body(item)
    published_url: Optional[str] = None
    error: Optional[str] = None

    try:
        if platform == "twitter":
            published_url = _post_twitter(body, creds)
        elif platform in ("webhook", "linkedin"):
            published_url = _post_webhook(item, creds)
        elif platform == "instagram":
            published_url = _post_instagram(body, creds)
        else:
            error = f"Platform '{platform}' is not supported for direct publishing. Use a webhook connector."
    except RuntimeError as exc:
        error = str(exc)
    except Exception as exc:
        safe = str(exc)[:200]
        error = f"Unexpected error during publish: {safe}"
        logger.exception("Unexpected publish error item=%s platform=%s", item_id, platform)

    # ── 5. Update item in DB ──────────────────────────────────────────────
    if published_url and not error:
        sb.table("scheduled_items").update({
            "status": "published",
            "published_at": now_iso,
            "published_url": published_url,
            "publish_error": None,
            "publish_attempted_at": now_iso,
            "updated_at": now_iso,
        }).eq("id", item_id).eq("user_id", user_id).execute()

        logger.info("Published item=%s platform=%s url=%s", item_id, platform, published_url)
        return PublishResult(
            success=True,
            item_id=item_id,
            platform=platform,
            published_url=published_url,
            published_at=now_iso,
        )
    else:
        _write_publish_error(sb, item_id, error or "Unknown error", now_iso)
        logger.warning("Publish failed item=%s platform=%s error=%s", item_id, platform, error)
        return PublishResult(success=False, item_id=item_id, platform=platform, error=error)


def _write_publish_error(sb, item_id: str, error: str, now_iso: str) -> None:
    """Write a publish error to scheduled_items without changing status."""
    try:
        sb.table("scheduled_items").update({
            "publish_error": error[:500],
            "publish_attempted_at": now_iso,
            "updated_at": now_iso,
        }).eq("id", item_id).execute()
    except Exception:
        logger.warning("Could not write publish_error for item=%s", item_id)


def run_due_posts(user_id: str, sb) -> RunDueResult:
    """Publish all scheduled items whose scheduled_at is in the past.

    Only processes items with status='scheduled' AND scheduled_at <= NOW().
    Failed items keep status='scheduled' (will retry on next run).

    Args:
        user_id: JWT-verified user ID (only publishes user's own items).
        sb: Supabase admin client.

    Returns:
        RunDueResult with published/failed/skipped counts and errors list.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    due_resp = (
        sb.table("scheduled_items")
        .select("id, platform, title")
        .eq("user_id", user_id)
        .eq("status", "scheduled")
        .lte("scheduled_at", now_iso)
        .order("scheduled_at")
        .limit(50)  # Safety cap — never process more than 50 at once
        .execute()
    )

    items = due_resp.data or []
    result = RunDueResult()

    if not items:
        return result

    for item in items:
        try:
            pr = publish_item(item_id=item["id"], user_id=user_id, sb=sb)
            if pr.success:
                result.published += 1
            else:
                result.failed += 1
                result.errors.append({"item_id": item["id"], "platform": item.get("platform"), "error": pr.error})
        except Exception as exc:
            result.failed += 1
            result.errors.append({"item_id": item["id"], "error": str(exc)[:200]})

    logger.info(
        "run_due_posts user=%s published=%d failed=%d",
        user_id, result.published, result.failed,
    )
    return result
