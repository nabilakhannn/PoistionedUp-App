"""Connectors service — Slice 85.

Manages per-user encrypted credentials for external services
(LinkedIn, Twitter/X, Instagram, custom webhooks).

Security:
  - Credentials are Fernet-encrypted (AES-128-CBC) before DB storage
  - Encryption key from CONNECTOR_ENCRYPTION_KEY env var
  - Raw credentials are NEVER logged or returned to the client
  - Webhook URLs are validated through validate_url() (SSRF protection)
  - Test errors return safe strings — never leak the actual credential

Supported services: linkedin, twitter, instagram, webhook
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.deps import get_admin_client
from app.utils.url_validation import validate_url_for_fetch as validate_url

logger = logging.getLogger("app.services.connectors")

SUPPORTED_SERVICES = {"linkedin", "twitter", "instagram", "webhook", "manus_ai"}

# ── Encryption helpers ────────────────────────────────────────────────────


def _get_fernet():
    """Return a Fernet instance or raise if key is missing."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise RuntimeError("cryptography package not installed — run: pip install cryptography>=43.0.0")

    key = settings.connector_encryption_key.strip()
    if not key:
        raise ValueError(
            "CONNECTOR_ENCRYPTION_KEY is not set. "
            "Generate one with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise ValueError(f"CONNECTOR_ENCRYPTION_KEY is invalid: {exc}") from exc


def encrypt_credentials(data: Dict[str, str]) -> str:
    """Encrypt a credentials dict → base64 ciphertext string."""
    f = _get_fernet()
    return f.encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(encrypted: str) -> Dict[str, str]:
    """Decrypt a ciphertext string → credentials dict."""
    f = _get_fernet()
    return json.loads(f.decrypt(encrypted.encode()).decode())


# ── Credential shape validation ───────────────────────────────────────────


_REQUIRED_FIELDS = {
    # LinkedIn: session_cookie still accepted for test (legacy); direct posting
    # routes through webhook — see publishing.py and Settings UI guidance.
    "linkedin": ["session_cookie"],
    # Twitter: OAuth 1.0a required for posting. Bearer tokens are read-only.
    "twitter": ["api_key", "api_secret", "access_token", "access_token_secret"],
    "instagram": ["access_token", "page_id"],
    "webhook": ["url"],
    "manus_ai": ["api_key"],
}


def _validate_credential_shape(service: str, creds: Dict[str, str]) -> None:
    """Raise ValueError if required fields are missing."""
    required = _REQUIRED_FIELDS.get(service, [])
    missing = [f for f in required if not creds.get(f, "").strip()]
    if missing:
        raise ValueError(f"Missing required fields for {service}: {missing}")

    # SSRF protection for webhook URLs
    if service == "webhook":
        url = creds.get("url", "").strip()
        validate_url(url)  # raises ValueError if private IP / invalid


# ── Service test helpers ──────────────────────────────────────────────────


def _test_linkedin(creds: Dict[str, str]) -> str:
    """Test LinkedIn session cookie via the /voyager/api/me endpoint."""
    try:
        resp = httpx.get(
            "https://www.linkedin.com/voyager/api/me",
            headers={
                "Cookie": f"li_at={creds['session_cookie']}",
                "Csrf-Token": "ajax:0",
                "X-RestLi-Protocol-Version": "2.0.0",
            },
            timeout=10.0,
            follow_redirects=False,
        )
        if resp.status_code == 200:
            return "ok"
        if resp.status_code in (401, 403):
            return "error: invalid or expired session cookie"
        return f"error: LinkedIn returned HTTP {resp.status_code}"
    except Exception:
        return "error: could not reach LinkedIn — check network or cookie"


def _test_twitter(creds: Dict[str, str]) -> str:
    """Test Twitter/X OAuth 1.0a credentials via get_me().

    Requires api_key, api_secret, access_token, access_token_secret.
    OAuth 1.0a is required for posting — bearer tokens are read-only.
    """
    # Check for old bearer_token shape (Slice 85 legacy)
    if "bearer_token" in creds and not creds.get("api_key"):
        return "error: credentials format updated — please re-enter your Twitter OAuth 1.0a keys (api_key, api_secret, access_token, access_token_secret) in Settings"

    required = ["api_key", "api_secret", "access_token", "access_token_secret"]
    missing = [f for f in required if not creds.get(f, "").strip()]
    if missing:
        return f"error: missing fields {missing}"

    try:
        import tweepy  # noqa: PLC0415
        client = tweepy.Client(
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            access_token=creds["access_token"],
            access_token_secret=creds["access_token_secret"],
        )
        me = client.get_me()
        if me and me.data:
            return "ok"
        return "error: could not retrieve user info"
    except ImportError:
        return "error: tweepy not installed — contact support"
    except Exception:
        return "error: invalid Twitter OAuth credentials — check all four keys"


def _test_instagram(creds: Dict[str, str]) -> str:
    """Test Instagram Graph API token via /me endpoint."""
    try:
        resp = httpx.get(
            "https://graph.facebook.com/v21.0/me",
            params={"access_token": creds["access_token"], "fields": "id,name"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            return "ok"
        if resp.status_code in (400, 401):
            return "error: invalid or expired access token"
        return f"error: Instagram Graph API returned HTTP {resp.status_code}"
    except Exception:
        return "error: could not reach Instagram Graph API"


def _test_webhook(creds: Dict[str, str]) -> str:
    """Ping webhook URL with a test payload."""
    url = creds.get("url", "").strip()
    try:
        validate_url(url)  # SSRF check before making the request
        resp = httpx.post(
            url,
            json={"event": "test", "source": "positionedup"},
            timeout=8.0,
        )
        if resp.status_code < 400:
            return "ok"
        return f"error: webhook returned HTTP {resp.status_code}"
    except ValueError as exc:
        return f"error: {exc}"
    except Exception:
        return "error: could not reach webhook URL"


def _test_manus_ai(creds: Dict[str, str]) -> str:
    """Test Manus AI API key by listing tasks."""
    api_key = creds.get("api_key", "").strip()
    if not api_key:
        return "error: API key is empty"
    try:
        resp = httpx.get(
            "https://api.manus.im/v1/tasks",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"limit": 1},
            timeout=10.0,
        )
        if resp.status_code == 200:
            return "ok"
        if resp.status_code in (401, 403):
            return "error: invalid API key"
        return f"error: Manus API returned HTTP {resp.status_code}"
    except Exception:
        return "error: could not reach Manus AI API"


_TEST_FUNCTIONS = {
    "linkedin": _test_linkedin,
    "twitter": _test_twitter,
    "instagram": _test_instagram,
    "webhook": _test_webhook,
    "manus_ai": _test_manus_ai,
}


# ── Public service functions ──────────────────────────────────────────────


def list_connectors(user_id: str) -> List[Dict[str, Any]]:
    """Return connectors for a user — NEVER includes raw credentials."""
    sb = get_admin_client()
    result = (
        sb.table("user_connectors")
        .select("id, service, display_name, is_active, last_tested_at, last_test_status, last_test_error, created_at, updated_at")
        .eq("user_id", user_id)
        .order("service")
        .execute()
    )
    return result.data or []


def save_connector(user_id: str, service: str, display_name: str, raw_credentials: Dict[str, str]) -> Dict[str, Any]:
    """Save (or update) a connector. Encrypts credentials before storage.

    Raises ValueError on invalid service, missing fields, or bad webhook URL.
    """
    if service not in SUPPORTED_SERVICES:
        raise ValueError(f"Unsupported service {service!r}. Choose from: {sorted(SUPPORTED_SERVICES)}")

    _validate_credential_shape(service, raw_credentials)
    encrypted = encrypt_credentials(raw_credentials)

    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()
    result = sb.table("user_connectors").upsert(
        {
            "user_id": user_id,
            "service": service,
            "display_name": display_name or service.title(),
            "encrypted_credentials": encrypted,
            "is_active": True,
            "last_test_status": "untested",
            "updated_at": now,
        },
        on_conflict="user_id,service",
    ).execute()

    if not result.data:
        raise RuntimeError("Failed to save connector")

    # Return safe (no credentials) row
    row = result.data[0]
    row.pop("encrypted_credentials", None)
    logger.info("Saved connector service=%s for user=%s", service, user_id)
    return row


def delete_connector(user_id: str, service: str) -> bool:
    """Delete a connector. Returns True if deleted, False if not found."""
    sb = get_admin_client()
    result = (
        sb.table("user_connectors")
        .delete()
        .eq("user_id", user_id)
        .eq("service", service)
        .execute()
    )
    deleted = bool(result.data)
    if deleted:
        logger.info("Deleted connector service=%s for user=%s", service, user_id)
    return deleted


def test_connector(user_id: str, service: str) -> Dict[str, Any]:
    """Decrypt credentials and ping the external service.

    Returns {"status": "ok" | "error", "message": "..."}
    — NEVER includes the raw credential in the response.
    """
    sb = get_admin_client()
    result = (
        sb.table("user_connectors")
        .select("encrypted_credentials")
        .eq("user_id", user_id)
        .eq("service", service)
        .limit(1)
        .execute()
    )
    if not result.data:
        return {"status": "error", "message": "Connector not found"}

    try:
        creds = decrypt_credentials(result.data[0]["encrypted_credentials"])
    except Exception:
        return {"status": "error", "message": "Failed to decrypt credentials — connector may be corrupt"}

    test_fn = _TEST_FUNCTIONS.get(service)
    if not test_fn:
        return {"status": "error", "message": f"No test available for service {service!r}"}

    test_result = test_fn(creds)  # Returns "ok" or "error: ..."
    status = "ok" if test_result == "ok" else "error"
    safe_message = test_result if test_result == "ok" else test_result  # Already safe — no raw creds

    # Update last_test_status in DB
    now = datetime.now(timezone.utc).isoformat()
    sb.table("user_connectors").update({
        "last_tested_at": now,
        "last_test_status": status,
        "last_test_error": None if status == "ok" else safe_message,
        "updated_at": now,
    }).eq("user_id", user_id).eq("service", service).execute()

    logger.info("Connector test service=%s user=%s result=%s", service, user_id, status)
    return {"status": status, "message": safe_message if status == "error" else "Connection successful"}
