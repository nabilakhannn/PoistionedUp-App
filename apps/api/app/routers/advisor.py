"""Advisor router — proactive content strategy suggestions."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, get_current_user
from app.services.advisor import get_suggestions

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.get("/suggestions")
def list_suggestions(
    brand_id: Optional[str] = None,
    limit: int = 5,
    user: CurrentUser = Depends(get_current_user),
) -> List[dict]:
    """Return proactive advisor suggestions for the current user/brand.

    Aggregates performance, memory, experiments, cadence, and schedule
    data to generate actionable next steps.
    """
    return get_suggestions(
        user_id=user.id,
        brand_id=brand_id,
        limit=min(limit, 10),
    )
