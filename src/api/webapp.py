"""Проксирование Flet Mini App через FastAPI.

Telegram требует, чтобы URL Mini App был публичным HTTPS-адресом.
Flet-сервер (webapp) поднят отдельно; данный роутер пробрасывает
запросы /app/* на него WebSocket/HTTP-проксированием через httpx,
так что наружу торчит только один порт API (удобно для Nginx).

В docker-compose webapp доступен по имени сервиса, в локальной
разработке — по 127.0.0.1:8550 (переменная WEBAPP_UPSTREAM_URL).
"""

import logging
import os

import httpx
from fastapi import APIRouter, Request, Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MiniApp proxy"])

# Адрес Flet-приложения внутри сети (в docker-compose — имя сервиса)
WEBAPP_UPSTREAM_URL = os.getenv("WEBAPP_UPSTREAM_URL", "http://127.0.0.1:8550")

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


@router.api_route(
    "/app",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
@router.api_route(
    "/app/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def proxy_webapp(request: Request, path: str = "") -> Response:
    """HTTP-прокси запроса к Flet-серверу Mini App."""
    url = f"{WEBAPP_UPSTREAM_URL}/{path}"

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    body = await request.body()

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        ) as client:
            upstream = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=request.query_params,
            )
    except httpx.HTTPError as exc:
        logger.error("Mini App недоступен (%s): %s", url, exc)
        return Response(
            content=b"Mini App is starting... retry in a few seconds.",
            status_code=502,
        )

    response_headers = {
        k: v
        for k, v in upstream.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
