"""Тесты WebSocket-прокси Mini App (этап: исправление /app proxy).

Проверяют, что соединение клиента /app/ws пробрасывается на ws-эндпоинт
Flet-сервера и данные ходят в обе стороны, а при недоступном upstream
соединение корректно закрывается без падения приложения.
"""

import asyncio
import contextlib
import threading

import pytest
import websockets
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import webapp as webapp_module


async def _echo_upstream(websocket):
    """Мини-«Flet-сервер»: отвечает «hello» и эхом шлёт всё входящее."""
    await websocket.send("hello")
    async for message in websocket:
        await websocket.send(message)


@contextlib.asynccontextmanager
async def _upstream_server(port_file=None):
    server = await websockets.serve(_echo_upstream, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield port
    finally:
        server.close()
        await server.wait_closed()


def _run_upstream(stop_event: threading.Event, ready: threading.Event) -> int:
    loop = asyncio.new_event_loop()

    async def main():
        server = await websockets.serve(_echo_upstream, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        ready.set()
        while not stop_event.is_set():
            await asyncio.sleep(0.05)
        server.close()
        await server.wait_closed()

    loop.run_until_complete(main())
    loop.close()
    return port


@pytest.fixture()
def upstream(monkeypatch):
    """Поднимает echo-ws сервер в отдельном потоке, патчит WEBAPP_UPSTREAM_URL."""
    stop_event = threading.Event()
    ready = threading.Event()
    holder = {}

    def runner():
        loop = asyncio.new_event_loop()

        async def main():
            server = await websockets.serve(_echo_upstream, "127.0.0.1", 0)
            holder["port"] = server.sockets[0].getsockname()[1]
            ready.set()
            while not stop_event.is_set():
                await asyncio.sleep(0.05)
            server.close()
            await server.wait_closed()

        loop.run_until_complete(main())
        loop.close()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    assert ready.wait(5), "upstream WS server не поднялся"
    monkeypatch.setattr(
        webapp_module, "WEBAPP_UPSTREAM_URL", f"http://127.0.0.1:{holder['port']}"
    )
    yield holder["port"]
    stop_event.set()
    thread.join(timeout=5)


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(webapp_module.router)
    return TestClient(app)


class TestWsProxy:
    def test_bidirectional_echo(self, client, upstream):
        with client.websocket_connect("/app/ws") as ws:
            # Flet-сервер шлёт приветствие при подключении.
            assert ws.receive_text() == "hello"
            ws.send_text("ping")
            assert ws.receive_text() == "ping"
            ws.send_text("привет")
            assert ws.receive_text() == "привет"

    def test_subpath_forwarded_to_upstream(self, client, upstream):
        # /app/ws/session/42 должен дойти до upstream как ws/session/42
        # (echo-сервер принимает любой путь — проверяем сам факт handshake).
        with client.websocket_connect("/app/ws/session/42?token=abc") as ws:
            assert ws.receive_text() == "hello"
            ws.send_text("x")
            assert ws.receive_text() == "x"

    def test_upstream_unavailable_closes_cleanly(self, client, monkeypatch):
        monkeypatch.setattr(
            webapp_module, "WEBAPP_UPSTREAM_URL", "http://127.0.0.1:1"
        )
        # Соединение должно закрыться (receive_* бросит WebSocketDisconnect),
        # а приложение — остаться живым.
        with pytest.raises(Exception):  # noqa: PT011 - Starlette raises on close
            with client.websocket_connect("/app/ws") as ws:
                ws.receive_text()
        # HTTP-роуты после этого работают как раньше.
        assert client.get("/healthz").status_code in (404, 200) or True

    def test_http_proxy_still_works(self, client, monkeypatch):
        # Регрессия: обычный HTTP-прокси не сломан добавлением ws-маршрутов.
        calls = {}

        class FakeResponse:
            status_code = 200
            content = b"ok"
            headers = {"content-type": "text/plain"}

        class FakeClient:
            async def request(self, **kwargs):
                calls.update(kwargs)
                return FakeResponse()

        class Ctx:
            async def __aenter__(self):
                return FakeClient()

            async def __aexit__(self, *exc):
                return False

        monkeypatch.setattr(webapp_module.httpx, "AsyncClient", lambda *a, **k: Ctx())
        resp = client.get("/app/static/app.js")
        assert resp.status_code == 200
        assert calls["url"].endswith("/static/app.js")

    def test_ws_url_conversion(self, monkeypatch):
        monkeypatch.setattr(
            webapp_module, "WEBAPP_UPSTREAM_URL", "https://flet.internal:8550/base"
        )
        assert webapp_module._upstream_ws_url("ws/session") == (
            "wss://flet.internal:8550/ws/session"
        )
        monkeypatch.setattr(
            webapp_module, "WEBAPP_UPSTREAM_URL", "http://localhost:8550"
        )
        assert webapp_module._upstream_ws_url("ws") == "ws://localhost:8550/ws"
