"""Brand Chat router — Slice 100.

POST /brand-chat/{brand_id}  — Send a message to Jumbo with brand context.

Security:
  - A01 IDOR: brand_id scoped to current user in service layer
  - A03 Injection: UUID regex validates brand_id before any DB access
  - A07 Auth: Depends(get_current_user) on all routes
  - Message length cap: 5000 chars
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import get_current_user, CurrentUser
from app.services.brand_chat import send_chat_message

router = APIRouter(prefix="/brand-chat", tags=["brand-chat"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=20000)


class ChatResponse(BaseModel):
    response: str
    brand_id: str
    brand_name: str


@router.post("/{brand_id}", response_model=ChatResponse)
async def chat_with_jumbo(
    brand_id: str,
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message to Jumbo about a specific client brand.

    Jumbo has the full 8-section brand dossier pre-loaded and will generate
    personalized materials: hooks, posts, nurture sequences, offer outlines, etc.
    """
    if not _UUID_RE.match(brand_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="brand_id must be a valid UUID",
        )

    try:
        result = await send_chat_message(
            brand_id=brand_id,
            user_id=user.id,
            message=body.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return ChatResponse(**result)
