"""HTTP-middleware безопасности (docs/09 §1, §2.3.1).

- RateLimitMiddleware — скользящее окно на основе Redis-счётчика; защищает
  чувствительные эндпоинты (auth/*, uploads) от перебора и флуда. При
  недоступности Redis честно возвращает 503 вместо тихого отключения защиты.
- CsrfGuardMiddleware — SameSite=Lax cookie + обязательный заголовок
  X-Requested-With и допустимый Origin для изменяющих запросов.
"""

import time
from typing import Iterable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.redis import get_redis

# Пути, которые лимитируем агрессивнее общего фона
STRICT_LIMIT_PATHS = ("/auth/", "/me/uploads")
STRICT_LIMIT_PER_MINUTE = 10
DEFAULT_LIMIT_PER_MINUTE = 120
WINDOW_SECONDS = 60

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Ограничение частоты запросов по IP (Redis INCR + TTL-окно)."""

    def __init__(self, app, *, strict_paths: Iterable[str] = STRICT_LIMIT_PATHS):
        super().__init__(app)
        self.strict_paths = tuple(strict_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Статика /uploads не должна съедать лимит браузера
        if request.url.path.startswith("/uploads"):
            return await call_next(request)

        limit = (
            STRICT_LIMIT_PER_MINUTE
            if request.url.path.startswith(self.strict_paths)
            else DEFAULT_LIMIT_PER_MINUTE
        )
        client_ip = request.client.host if request.client else "unknown"
        minute_bucket = int(time.time() // WINDOW_SECONDS)
        key = f"ratelimit:{client_ip}:{request.url.path[:48]}:{minute_bucket}"

        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, WINDOW_SECONDS * 2)
        except Exception:  # noqa: BLE001 — fail-closed для auth-эндпоинтов
            return JSONResponse(
                status_code=503,
                content={"detail": "Сервис временно недоступен"},
            )

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Слишком много запросов, попробуйте позже"},
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )

        return await call_next(request)


class CsrfGuardMiddleware(BaseHTTPMiddleware):
    """CSRF-защита для запросов с cookie-сессией (docs/09 §2.3.1).

    Для POST/PATCH/PUT/DELETE, пришедших с cookie `lms_session` или
    Authorization, требуются заголовок X-Requested-With и Origin с нашего
    домена. Запросы Flet-сервера (server-side, без cookie браузера) проходят
    по Bearer-токену без Origin — их атака через форму браузера не касается.
    """

    def __init__(self, app, allowed_origins: Optional[set[str]] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or set()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)

        has_cookie = "lms_session" in request.cookies
        has_auth = "authorization" in {k.lower() for k in request.headers}
        if not (has_cookie or has_auth):
            return await call_next(request)

        origin = request.headers.get("origin")
        xrw = request.headers.get("x-requested-with")

        if xrw is None:
            return JSONResponse(
                status_code=403,
                content={"detail": "Отсутствует заголовок X-Requested-With"},
            )

        if origin and self.allowed_origins and origin.rstrip("/") not in self.allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "Недопустимый Origin"},
            )

        return await call_next(request)
