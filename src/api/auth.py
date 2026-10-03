"""Аутентификация Mini App (docs/09 §2.2).

Единственный способ войти в веб-интерфейс — присланная Telegram строка
``initData``, подпись которой проверена HMAC-ключом от токена бота. Сырой
telegram_id без подписи не принимается никогда.

Результат входа — серверная сессия в Redis; клиент получает только
HttpOnly-cookie ``lms_session`` (JS к ней доступа не имеет). Короткоживущий
JWT выдаётся исключительно server-side клиенту (Flet), который ходит в API
от имени вошедшего пользователя; в браузер он не попадает.

Парольный вход (/auth/login) удалён: docs/09 §2.4 прямо запрещает пароли.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.schemas import (
    WebAppIdentifyRequest,
    WebAppIdentifyResponse,
    WebAppLogoutResponse,
)
from src.core.config import settings
from src.services.auth import AuthService
from src.services.sessions import session_service, write_audit
from src.services.telegram_init_data import InitDataError, verify_init_data

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

SESSION_COOKIE_NAME = "lms_session"


@router.post(
    "/webapp-identify",
    response_model=WebAppIdentifyResponse,
)
async def webapp_identify(
    data: WebAppIdentifyRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> WebAppIdentifyResponse:
    """Идентификация пользователя Mini App по **верифицированной** initData.

    Flet-сервер не имеет прямого доступа к БД (docs/03_architecture.md):
    он передаёт сюда сырую строку ``initData`` из window.Telegram.WebApp,
    сервер проверяет подпись (HMAC, auth_date ≤ 24 ч) и только затем
    находит пользователя по telegram_id из *подписанных* данных.

    Поле ``telegram_id`` в запросе считается справочным: если оно не
    совпадает с подписанным — это попытка подмены, запрос отклоняется.
    """
    try:
        verified = verify_init_data(data.init_data, settings.bot_token.get_secret_value())
    except InitDataError as exc:
        # Не отдаём деталей подписи клиенту — только факт отказа.
        await write_audit(
            "auth.webapp_identify_rejected",
            details={"reason": str(exc)},
            ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Подпись initData не подтверждена",
        ) from exc

    signed_tg_id = verified["telegram_id"]

    if data.telegram_id is not None and data.telegram_id != signed_tg_id:
        await write_audit(
            "auth.telegram_id_mismatch",
            details={"claimed": data.telegram_id, "signed": signed_tg_id},
            ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Несовпадение заявленного и подписанного telegram_id",
        )

    auth = AuthService()
    user = await auth.get_user_by_telegram_id(session, signed_tg_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Попросите преподавателя отправить приглашение.",
        )

    # Серверная сессия + HttpOnly-cookie (docs/09 §2.2, §2.3)
    session_id, ttl = await session_service.create(
        user_id=user.id, role=user.role.value
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=ttl,
        httponly=True,
        secure=settings.is_production,   # HTTPS-only в проде
        samesite="lax",
        path="/",
    )

    await write_audit("auth.webapp_identify_ok", user_id=user.id)

    return WebAppIdentifyResponse(
        # JWT — только для server-side вызовов Flet-приложения; в UI не кладётся.
        access_token=auth.create_access_token(user),
        token_type="bearer",
        user={
            "id": user.id,
            "login": user.login,
            "role": user.role.value,
        },
    )


@router.post("/logout", response_model=WebAppLogoutResponse)
async def logout(request: Request, response: Response) -> WebAppLogoutResponse:
    """Выход: удалить серверную сессию в Redis и снять cookie."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        await session_service.revoke(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return WebAppLogoutResponse(ok=True)
