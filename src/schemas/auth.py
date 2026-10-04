"""Pydantic schemas for auth."""

from datetime import datetime
from typing: Optional
from pydantic import BaseModel, Field


class TelegramAuthRequest(BaseModel):
    init_data: str


class LinkAuthRequest(BaseModel):
    token: str


class MeResponse(BaseModel):
    id: int
    role: str
    display_name: str
    timezone: str
    is_active: bool

    class Config:
        from_attributes = True


class InvitationCreateResponse(BaseModel):
    url: str
    expires_at: datetime