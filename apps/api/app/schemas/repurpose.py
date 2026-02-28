"""Pydantic schemas for the Content Repurposing system."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


VALID_SOURCE_PLATFORMS = {
    "youtube", "linkedin", "twitter", "tiktok", "instagram", "blog", "email", "other",
}

VALID_TARGET_PLATFORMS = {
    "linkedin", "twitter", "instagram", "tiktok", "facebook",
    "ad_copy", "carousel", "email", "blog",
}


class RepurposeRequest(BaseModel):
    source_id: Optional[str] = Field(
        None, description="ID of a scheduled_item or content_asset to repurpose",
    )
    source_text: Optional[str] = Field(
        None, max_length=50000, description="Raw text to repurpose (alternative to source_id)",
    )
    source_platform: str = Field(
        ..., description="Platform the source content was originally created for",
    )
    target_platforms: List[str] = Field(
        ..., min_length=1, max_length=8, description="Platforms to repurpose into",
    )
    brand_id: Optional[str] = None
    auto_schedule: bool = Field(
        False, description="Automatically create draft schedule items for each repurposed piece",
    )

    @field_validator("source_platform")
    @classmethod
    def validate_source_platform(cls, v: str) -> str:
        if v not in VALID_SOURCE_PLATFORMS:
            raise ValueError(f"Invalid source_platform: {v}. Valid: {sorted(VALID_SOURCE_PLATFORMS)}")
        return v

    @field_validator("target_platforms")
    @classmethod
    def validate_target_platforms(cls, v: List[str]) -> List[str]:
        invalid = set(v) - VALID_TARGET_PLATFORMS
        if invalid:
            raise ValueError(f"Invalid target platforms: {sorted(invalid)}. Valid: {sorted(VALID_TARGET_PLATFORMS)}")
        return v


class RepurposedItem(BaseModel):
    platform: str
    content_type: str
    title: str
    body: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RepurposeResponse(BaseModel):
    source_platform: str
    repurposed: List[RepurposedItem]
    scheduled_items_created: int = 0


class PlatformInfo(BaseModel):
    platform: str
    content_type: str
    char_limit: Optional[int] = None
    description: str
