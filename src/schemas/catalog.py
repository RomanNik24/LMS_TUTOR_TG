"""Pydantic schemas for catalog."""


from pydantic import BaseModel, Field


class CatalogItemCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: str
    price_text: str | None = None
    sort_order: int = 0


class CatalogItemUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    price_text: str | None = None
    sort_order: int | None = None
    is_published: bool | None = None


class CatalogItemResponse(BaseModel):
    id: int
    title: str
    description: str
    price_text: str | None
    sort_order: int
    is_published: bool

    class Config:
        from_attributes = True
