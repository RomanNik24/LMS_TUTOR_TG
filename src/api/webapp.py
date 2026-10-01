"""Проксирование Flet Mini App через FastAPI.

Telegram требует, чтобы URL Mini App был публичным HTTPS-адресом.
Flet-сервер (webapp) поднят отдельно; данный роутер пробрасывает на него:

* HTTP-запросы /app/* — через httpx;
* WebSocket-соединения /app/ws — через websockets (фреймворк flet-web
  общается с сервером именно по WebSocket, поэтому без WS-прокси Mini App
  через этот маршрут не работает).

В docker-compose webapp доступен по имени сервиса, в локальной
разработке — по 127.0.0.1:8550 (переменная WEBAPP_UPSTREAM_URL).
"""

import asyncio
import logging
from urllib.parse import urlparse

import httpx
import websockets
from fastapi import (
    APIRouter,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MiniApp proxy"])

# Адрес Flet-приложения внутри сети (в docker-compose — имя сервиса)
from src.core.config import settings

# Единый источник конфигурации — поле Settings.webapp_upstream_url
# (переменная окружения WEBAPP_UPSTREAM_URL). Раньше здесь был прямой
# os.getenv, из-за чего переменная не была описана в Settings и её
# нельзя было проверить/документировать наравне с остальными.
WEBAPP_UPSTREAM_URL = settings.webapp_upstream_url

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


def _upstream_ws_url(path: str) -> str:
    """HTTP(S)-адрес upstream -> WS(S)-адрес для того же пути."""
    parsed = urlparse(WEBAPP_UPSTREAM_URL)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/{path.lstrip('/')}"


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


@router.websocket("/app/ws")
@router.websocket("/app/ws/{path:path}")
async def proxy_webapp_ws(websocket: WebSocket, path: str = "") -> None:
    """WebSocket-прокси соединения клиента к ws-эндпоинту Flet-сервера.

    flet-web устанавливает соединение на <server>/ws[/...], поэтому путь
    после /app/ws пробрасывается upstream как есть (upstream-путь = "ws/...").
    """
    query = websocket.url.query
    # Нормализуем: "/app/ws" -> "ws", "/app/ws/foo" -> "ws/foo".
    full_path = websocket.url.path.lstrip("/")
    upstream_path = full_path[len("app/"):] if full_path.startswith("app/") else full_path
    upstream_url = _upstream_ws_url(upstream_path)
    if query:
        upstream_url = f"{upstream_url}?{query}"

    # Пробрасываем клиентские заголовки, кроме hop-by-hop и обязательных
    # заголовков самого handshake (их websockets client генерирует сам).
    forwarded_headers = {
        k: v
        for k, v in websocket.headers.items()
        if k.lower() not in _HOP_BY_HOP
        and k.lower()
        not in {
            "host",
            "sec-websocket-key",
            "sec-websocket-version",
            "sec-websocket-extensions",
        }
    }

    await websocket.accept()

    try:
        async with websockets.connect(
            upstream_url,
            additional_headers=forwarded_headers,
            max_size=None,
            ping_interval=None,
        ) as upstream_ws:
            logger.info("WS proxy established: %s -> %s", websocket.url, upstream_url)

            async def client_to_upstream() -> None:
                try:
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            break
                        if message.get("text") is not None:
                            await upstream_ws.send(message["text"])
                        elif message.get("bytes") is not None:
                            await upstream_ws.send(message["bytes"])
                finally:
                    # Клиент отключился — закрываем upstream.
                    await upstream_ws.close()

            async def upstream_to_client() -> None:
                try:
                    async for raw in upstream_ws:
                        if isinstance(raw, bytes):
                            await websocket.send_bytes(raw)
                        else:
                            await websocket.send_text(raw)
                finally:
                    try:
                        await websocket.close()
                    except RuntimeError:
                        # Соединение уже закрыто другой задачей/клиентом.
                        pass

            tasks = [
                asyncio.ensure_future(client_to_upstream()),
                asyncio.ensure_future(upstream_to_client()),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            # CancelledError при штатном закрытии — ожидаемая ситуация.
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                exc = task.exception()
                if exc is not None and not isinstance(
                    exc,
                    (WebSocketDisconnect, websockets.exceptions.ConnectionClosed),
                ):
                    logger.warning("WS proxy task finished with error: %r", exc)
    except websockets.exceptions.WebSocketException as exc:
        logger.error("Upstream WS недоступен (%s): %s", upstream_url, exc)
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in WS proxy")
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
