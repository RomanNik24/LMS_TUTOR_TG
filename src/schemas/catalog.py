"""Pydantic schemas for catalog."""

from typing: Optional
from pydantic import BaseModel, Field


class CatalogItemCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: str
    price_text: Optional[str] = None
    sort_order: int = 0


class CatalogItemUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    price_text: Optional[str] = None
    sort_order: Optional[int] = None
    is_published: Optional[bool] = None


class CatalogItemResponse(BaseModel):
    id: int
    title: str
    description: str
    price_text: Optional[str]
    sort_order: int
    is_published: bool

    class Config:
        from_attributes = True