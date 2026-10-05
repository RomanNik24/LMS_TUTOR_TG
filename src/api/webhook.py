"""Telegram webhook endpoint."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from src.core.config import settings

router = APIRouter()


@router.post("/telegram/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
):
    if secret != settings.WEBHOOK_PATH_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook path secret")
    if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret token")

    # TODO: Process update with Aiogram dispatcher
    return {"ok": True}
