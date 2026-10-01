"""Этап: WS-прокси /app/ws (flet-web).

Проверяет, что WebSocket Mini App действительно проксируется на upstream
(flet-web слушает <server>/ws), а не только HTTP-запросы.
"""

import asyncio
import json

import pytest
import websockets
from fastapi.testclient import TestClient

from src.api import webapp as webapp_module


@pytest.fixture()
def fake_flet_server():
    """Подменяем WEBAPP_UPSTREAM_URL на локальный фейковый ws/http сервер."""
    return None  # unused placeholder to keep fixture list readable


def test_http_proxy_still_works(monkeypatch):
    """HTTP-часть прокси осталась рабочей (502 при недоступном upstream)."""
    monkeypatch.setattr(webapp_module, "WEBAPP_UPSTREAM_URL", "http://127.0.0.1:1")
    from src.main import app

    client = TestClient(app)
    resp = client.get("/app/")
    assert resp.status_code == 502
    assert b"Mini App" in resp.content


def test_websocket_proxy_roundtrip(monkeypatch):
    """WS-клиент -> /app/ws -> upstream /ws -> обратно (echo pong)."""
    import threading

    async def handler(ws):
        async for message in ws:
            data = json.loads(message)
            if data.get("action") == "ping":
                await ws.send(json.dumps({"op": "pong", "id": data.get("id")}))
            else:
                await ws.send(json.dumps({"op": "echo", "payload": data}))

    ready = threading.Event()
    holder = {}

    def run_server():
        loop = asyncio.new_event_loop()

        async def main():
            server = await websockets.serve(handler, "127.0.0.1", 0)
            holder["port"] = server.sockets[0].getsockname()[1]
            holder["server"] = server
            ready.set()
            await asyncio.Future()  # keep serving

        try:
            loop.run_until_complete(main())
        except asyncio.CancelledError:
            pass
        finally:
            loop.close()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    assert ready.wait(5), "fake upstream не поднялся"
    port = holder["port"]
    monkeypatch.setattr(
        webapp_module, "WEBAPP_UPSTREAM_URL", f"http://127.0.0.1:{port}"
    )

    try:
        from src.main import app

        client = TestClient(app)
        with client.websocket_connect("/app/ws?token=abc") as ws_client:
            ws_client.send_text(json.dumps({"action": "ping", "id": 42}))
            reply = json.loads(ws_client.receive_text())
            assert reply == {"op": "pong", "id": 42}

            ws_client.send_text(json.dumps({"action": "hello", "id": 43}))
            reply2 = json.loads(ws_client.receive_text())
            assert reply2["op"] == "echo"
            assert reply2["payload"]["action"] == "hello"
    finally:
        holder["server"].close()


def test_ws_upstream_unavailable_closes_with_1011(monkeypatch):
    """Если Flet-сервер ещё не поднялся — соединение закрывается кодом 1011."""
    monkeypatch.setattr(webapp_module, "WEBAPP_UPSTREAM_URL", "http://127.0.0.1:1")
    from src.main import app

    client = TestClient(app)
    from starlette.websockets import WebSocketDisconnect as StarletteDisconnect

    with pytest.raises(StarletteDisconnect) as exc_info:
        with client.websocket_connect("/app/ws") as ws:
            ws.receive_text()
    assert exc_info.value.code == 1011
