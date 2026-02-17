"""OAuth routes for Google Docs and Notion integrations.

Flow:
  1. GET /oauth/google/auth-url  -> returns redirect URL to Google consent
  2. GET /oauth/google/callback  -> exchanges code for tokens, stores in DB
  3. GET /oauth/google/status     -> checks if user has connected Google
  4. DELETE /oauth/google/disconnect -> removes tokens

Same pattern for Notion.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.oauth")

router = APIRouter(prefix="/oauth", tags=["oauth"])


# ── Response models ────────────────────────────────────


class AuthURLResponse(BaseModel):
    url: str
    provider: str


class OAuthStatusResponse(BaseModel):
    connected: bool
    provider: str
    scopes: list = []
    email: Optional[str] = None


class DisconnectResponse(BaseModel):
    message: str
    provider: str


# ── Google OAuth ──────────────────────────────────────


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
]


@router.get("/google/auth-url", response_model=AuthURLResponse)
async def google_auth_url(
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a Google OAuth consent URL for the user to authorize."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env",
        )

    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_SCOPES,
    )
    flow.redirect_uri = f"{settings.cors_origins[0]}/oauth/google/callback"

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=user.id,
    )

    return AuthURLResponse(url=auth_url, provider="google")


@router.post("/google/callback")
async def google_callback(
    code: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Exchange the authorization code for tokens and store them."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured.",
        )

    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_SCOPES,
    )
    flow.redirect_uri = f"{settings.cors_origins[0]}/oauth/google/callback"

    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error("Google token exchange failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code. Try connecting again.",
        )

    credentials = flow.credentials
    token_data = {
        "user_id": user.id,
        "provider": "google",
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token or "",
        "token_expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
        "scopes": list(credentials.scopes) if credentials.scopes else GOOGLE_SCOPES,
        "metadata": {},
    }

    admin = get_admin_client()

    # Upsert: if user already connected Google, update tokens
    existing = (
        admin.table("oauth_tokens")
        .select("id")
        .eq("user_id", user.id)
        .eq("provider", "google")
        .execute()
    )

    if existing.data:
        admin.table("oauth_tokens").update({
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "token_expires_at": token_data["token_expires_at"],
            "scopes": token_data["scopes"],
        }).eq("id", existing.data[0]["id"]).execute()
    else:
        admin.table("oauth_tokens").insert(token_data).execute()

    logger.info("Google OAuth tokens stored for user %s", user.id)
    return {"message": "Google account connected successfully", "provider": "google"}


@router.get("/google/status", response_model=OAuthStatusResponse)
async def google_status(
    user: CurrentUser = Depends(get_current_user),
):
    """Check if the user has connected their Google account."""
    admin = get_admin_client()
    resp = (
        admin.table("oauth_tokens")
        .select("scopes, metadata")
        .eq("user_id", user.id)
        .eq("provider", "google")
        .execute()
    )

    if resp.data:
        return OAuthStatusResponse(
            connected=True,
            provider="google",
            scopes=resp.data[0].get("scopes", []),
        )
    return OAuthStatusResponse(connected=False, provider="google")


@router.delete("/google/disconnect", response_model=DisconnectResponse)
async def google_disconnect(
    user: CurrentUser = Depends(get_current_user),
):
    """Disconnect the user's Google account (delete tokens)."""
    admin = get_admin_client()
    admin.table("oauth_tokens").delete().eq("user_id", user.id).eq("provider", "google").execute()
    return DisconnectResponse(message="Google account disconnected", provider="google")


# ── Notion OAuth ──────────────────────────────────────

NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"


@router.get("/notion/auth-url", response_model=AuthURLResponse)
async def notion_auth_url(
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a Notion OAuth consent URL."""
    if not settings.notion_client_id or not settings.notion_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion OAuth is not configured. Add NOTION_CLIENT_ID and NOTION_CLIENT_SECRET to .env",
        )

    redirect_uri = settings.notion_redirect_uri
    url = (
        f"{NOTION_AUTH_URL}"
        f"?client_id={settings.notion_client_id}"
        f"&response_type=code"
        f"&owner=user"
        f"&redirect_uri={redirect_uri}"
        f"&state={user.id}"
    )

    return AuthURLResponse(url=url, provider="notion")


@router.post("/notion/callback")
async def notion_callback(
    code: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Exchange Notion authorization code for an access token."""
    if not settings.notion_client_id or not settings.notion_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion OAuth is not configured.",
        )

    import httpx
    import base64

    # Notion uses Basic auth (client_id:client_secret)
    credentials_b64 = base64.b64encode(
        f"{settings.notion_client_id}:{settings.notion_client_secret}".encode()
    ).decode()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                NOTION_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials_b64}",
                    "Content-Type": "application/json",
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.notion_redirect_uri,
                },
            )
            resp.raise_for_status()
            token_resp = resp.json()
    except Exception as e:
        logger.error("Notion token exchange failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Notion authorization code. Try connecting again.",
        )

    access_token = token_resp.get("access_token", "")
    workspace_name = token_resp.get("workspace_name", "")
    workspace_id = token_resp.get("workspace_id", "")

    token_data = {
        "user_id": user.id,
        "provider": "notion",
        "access_token": access_token,
        "refresh_token": "",
        "scopes": [],
        "metadata": {
            "workspace_name": workspace_name,
            "workspace_id": workspace_id,
            "bot_id": token_resp.get("bot_id", ""),
        },
    }

    admin = get_admin_client()

    existing = (
        admin.table("oauth_tokens")
        .select("id")
        .eq("user_id", user.id)
        .eq("provider", "notion")
        .execute()
    )

    if existing.data:
        admin.table("oauth_tokens").update({
            "access_token": token_data["access_token"],
            "metadata": token_data["metadata"],
        }).eq("id", existing.data[0]["id"]).execute()
    else:
        admin.table("oauth_tokens").insert(token_data).execute()

    logger.info("Notion OAuth tokens stored for user %s", user.id)
    return {
        "message": "Notion account connected successfully",
        "provider": "notion",
        "workspace_name": workspace_name,
    }


@router.get("/notion/status", response_model=OAuthStatusResponse)
async def notion_status(
    user: CurrentUser = Depends(get_current_user),
):
    """Check if the user has connected their Notion account."""
    admin = get_admin_client()
    resp = (
        admin.table("oauth_tokens")
        .select("metadata")
        .eq("user_id", user.id)
        .eq("provider", "notion")
        .execute()
    )

    if resp.data:
        return OAuthStatusResponse(
            connected=True,
            provider="notion",
        )
    return OAuthStatusResponse(connected=False, provider="notion")


@router.delete("/notion/disconnect", response_model=DisconnectResponse)
async def notion_disconnect(
    user: CurrentUser = Depends(get_current_user),
):
    """Disconnect the user's Notion account (delete tokens)."""
    admin = get_admin_client()
    admin.table("oauth_tokens").delete().eq("user_id", user.id).eq("provider", "notion").execute()
    return DisconnectResponse(message="Notion account disconnected", provider="notion")


# ── Token helpers (used by export services) ────────────


def get_google_credentials(user_id: str):
    """Retrieve and refresh Google credentials for a user. Returns google.oauth2.credentials.Credentials or None."""
    admin = get_admin_client()
    resp = (
        admin.table("oauth_tokens")
        .select("access_token, refresh_token, token_expires_at, scopes")
        .eq("user_id", user_id)
        .eq("provider", "google")
        .execute()
    )

    if not resp.data:
        return None

    row = resp.data[0]

    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=row["access_token"],
        refresh_token=row.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=row.get("scopes", GOOGLE_SCOPES),
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            from google.auth.transport.requests import Request
            creds.refresh(Request())

            # Update stored tokens
            admin.table("oauth_tokens").update({
                "access_token": creds.token,
                "token_expires_at": creds.expiry.isoformat() if creds.expiry else None,
            }).eq("user_id", user_id).eq("provider", "google").execute()
        except Exception as e:
            logger.warning("Failed to refresh Google token for user %s: %s", user_id, e)
            return None

    return creds


def get_notion_token(user_id: str) -> Optional[str]:
    """Retrieve the Notion access token for a user. Returns token string or None."""
    admin = get_admin_client()
    resp = (
        admin.table("oauth_tokens")
        .select("access_token")
        .eq("user_id", user_id)
        .eq("provider", "notion")
        .execute()
    )

    if not resp.data:
        return None

    return resp.data[0]["access_token"]
