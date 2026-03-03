"""Connectors router — Slice 85.

Endpoints:
  GET    /connectors/                list (no raw credentials ever returned)
  POST   /connectors/{service}       save/update (encrypts on write)
  DELETE /connectors/{service}       remove connector
  POST   /connectors/{service}/test  test connectivity
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connectors", tags=["connectors"])


class SaveConnectorBody(BaseModel):
    display_name: Optional[str] = None
    credentials: Dict[str, str]  # service-specific fields, encrypted on write


# ── GET /connectors/ ──────────────────────────────────────────────

@router.get("/")
async def list_connectors(user: CurrentUser = Depends(get_current_user)):
    """List all connectors for the user. Never returns raw credentials."""
    from app.services.connectors import list_connectors as _list
    return _list(user.id)


# ── POST /connectors/{service} ────────────────────────────────────

@router.post("/{service}")
async def save_connector(
    service: str,
    body: SaveConnectorBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Save or update a connector. Credentials are encrypted before storage."""
    from app.services.connectors import save_connector as _save
    try:
        connector = _save(user.id, service, body.display_name or "", body.credentials)
        return {"status": "saved", "connector": connector}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── DELETE /connectors/{service} ──────────────────────────────────

@router.delete("/{service}")
async def delete_connector(
    service: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Remove a connector and its encrypted credentials."""
    from app.services.connectors import delete_connector as _delete
    deleted = _delete(user.id, service)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Connector {service!r} not found")
    return {"status": "deleted", "service": service}


# ── POST /connectors/{service}/test ──────────────────────────────

@router.post("/{service}/test")
async def test_connector(
    service: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Test a connector's credentials by pinging the external service."""
    from app.services.connectors import test_connector as _test
    result = _test(user.id, service)
    # Always return 200 — status field contains ok/error
    return result
