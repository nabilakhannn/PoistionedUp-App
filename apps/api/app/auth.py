"""JWT authentication via Supabase Auth."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

from app.deps import get_admin_client


@dataclass
class CurrentUser:
    id: str
    email: str


async def get_current_user(request: Request) -> CurrentUser:
    """Extract and validate JWT from Authorization header.

    Calls Supabase auth.get_user(token) which verifies the JWT
    signature and returns the user.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
        )

    admin = get_admin_client()
    try:
        resp = admin.auth.get_user(token)
    except Exception as e:
        # Log the actual error for debugging but return 401 to client
        import logging
        logging.getLogger("app.auth").warning("Token validation failed: %s: %s", type(e).__name__, e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if not resp or not resp.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return CurrentUser(id=resp.user.id, email=resp.user.email or "")
