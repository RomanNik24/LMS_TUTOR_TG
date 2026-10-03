"""Тесты этапа безопасности (docs/09 §1, §2).

- верификация initData: bad hash / stale auth_date / mismatch telegram_id → 401;
- серверные сессии в Redis (fakeredis) + HttpOnly-cookie;
- отзыв сессий (logout и revoke_all_for_user);
- rate limiting → 429;
- CSRF-guard → 403 для cookie-запросов без X-Requested-With.
"""

import time

import pytest

from src.core.config import settings
from src.db.models import RoleEnum, User
from src.services.sessions import session_service
from conftest import sign_init_data

BOT_TOKEN = settings.bot_token.get_secret_value()


async def _create_user(session_maker, *, tg_id: int, role=RoleEnum.student, login="u"):
    async with session_maker() as session:
        user = User(role=role, login=login, telegram_id=tg_id)
        session.add(user)
        await session.commit()
        return user.id


def _sec_headers():
    """Заголовки, проходящие CSRF-guard (server-side клиент Flet)."""
    return {"X-Requested-With": "XMLHttpRequest"}


class TestInitDataVerification:
    async def test_valid_init_data_sets_httponly_cookie(self, make_client):
        client, session_maker = make_client
        await _create_user(session_maker, tg_id=1001, login="alice")

        init_data = sign_init_data(BOT_TOKEN, 1001)
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": init_data},
            headers=_sec_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["login"] == "alice"
        assert body["access_token"]
        cookie_header = resp.headers.get("set-cookie", "")
        assert "lms_session=" in cookie_header
        assert "HttpOnly" in cookie_header
        assert "SameSite=lax" in cookie_header.lower().replace("samesite=lax", "SameSite=lax") or "samesite=lax" in cookie_header.lower()

    async def test_bad_hash_rejected(self, make_client):
        """Подделанный hash (классическая атака) — 401, JWT не выдан."""
        client, session_maker = make_client
        await _create_user(session_maker, tg_id=1002, login="bob")

        init_data = sign_init_data(BOT_TOKEN, 1002)
        tampered = init_data.replace("hash=", "hash=deadbeef") if "hash=deadbeef" not in init_data else init_data
        # Надёжнее: пересобрать строку с чужим user, оставив старый hash
        good = dict(p.split("=", 1) for p in init_data.split("&"))
        forged = f"user=%7B%22id%22%3A+1002%7D&auth_date={int(time.time())}&hash=0000000000000000000000000000000000000000000000000000000000000000"
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": forged},
            headers=_sec_headers(),
        )
        assert resp.status_code == 401
        assert "access_token" not in resp.json()

    async def test_stale_auth_date_rejected(self, make_client):
        """auth_date старше 24 часов — подпись больше не принимается."""
        client, session_maker = make_client
        await _create_user(session_maker, tg_id=1003, login="carol")

        old = int(time.time()) - 25 * 3600
        init_data = sign_init_data(BOT_TOKEN, 1003, auth_date=old)
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": init_data},
            headers=_sec_headers(),
        )
        assert resp.status_code == 401

    async def test_telegram_id_mismatch_rejected(self, make_client):
        """Заявленный telegram_id ≠ подписанному — попытка подмены, 401."""
        client, session_maker = make_client
        victim_id = await _create_user(session_maker, tg_id=1004, login="victim")

        init_data = sign_init_data(BOT_TOKEN, 9999)  # подписан чужой id
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": init_data, "telegram_id": 1004},
            headers=_sec_headers(),
        )
        assert resp.status_code == 401

    async def test_raw_telegram_id_without_init_data_rejected(self, make_client):
        """Сырой telegram_id без initData не принимается никогда."""
        client, session_maker = make_client
        await _create_user(session_maker, tg_id=1005, login="dave")

        resp = await client.post(
            "/auth/webapp-identify",
            json={"telegram_id": 1005},
            headers=_sec_headers(),
        )
        # 422: обязательное поле init_data отсутствует
        assert resp.status_code == 422

    async def test_unknown_user_404(self, make_client):
        client, _ = make_client
        init_data = sign_init_data(BOT_TOKEN, 123456789)
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": init_data},
            headers=_sec_headers(),
        )
        assert resp.status_code == 404


class TestSessionRevocation:
    async def test_logout_revokes_server_session(self, make_client):
        client, session_maker = make_client
        await _create_user(session_maker, tg_id=2001, login="erin")

        init_data = sign_init_data(BOT_TOKEN, 2001)
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": init_data},
            headers=_sec_headers(),
        )
        assert resp.status_code == 200
        sid = resp.cookies.get("lms_session")
        assert sid
        assert await session_service.get(sid) is not None

        resp = await client.post("/auth/logout", headers=_sec_headers())
        assert resp.status_code == 200
        assert await session_service.get(sid) is None

    async def test_revoke_all_for_user(self, make_client):
        """Отзыв всех сессий пользователя (ротация/подозрение на компрометацию)."""
        client, session_maker = make_client
        uid = await _create_user(session_maker, tg_id=2002, login="frank")

        s1, _ = await session_service.create(user_id=uid, role="student")
        s2, _ = await session_service.create(user_id=uid, role="student")
        other, _ = await session_service.create(user_id=999999, role="student")

        revoked = await session_service.revoke_all_for_user(uid)
        assert revoked >= 2
        assert await session_service.get(s1) is None
        assert await session_service.get(s2) is None
        assert await session_service.get(other) is not None  # чужие не тронуты


class TestRateLimit:
    async def test_auth_endpoint_returns_429_after_limit(self, make_client):
        """/auth/* лимитируется агрессивнее общего фона (10/мин)."""
        client, _ = make_client
        statuses = []
        for _ in range(12):
            resp = await client.post(
                "/auth/webapp-identify",
                json={"init_data": "hash=x&auth_date=1&user=%7B%7D"},
                headers=_sec_headers(),
            )
            statuses.append(resp.status_code)
        assert 401 in statuses          # первые запросы доходят до логики
        assert 429 in statuses          # после превышения лимита — Too Many Requests
        limited = [s for s in statuses if s == 429]
        assert len(limited) >= 1

    async def test_rate_limit_isolated_per_test(self, fake_redis):
        """Фикстура fakeredis даёт чистое окно лимита каждый тест."""
        keys = await fake_redis.keys("ratelimit:*")
        assert keys == []


class TestCsrfGuard:
    async def test_cookie_post_without_xrw_rejected(self, make_client):
        """POST с cookie-сессией и без X-Requested-With — 403 (docs/09 §2.3.1)."""
        client, session_maker = make_client
        await _create_user(session_maker, tg_id=3001, login="grace")

        init_data = sign_init_data(BOT_TOKEN, 3001)
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": init_data},
            headers=_sec_headers(),
        )
        assert resp.status_code == 200  # cookie установлена в cookie-jar клиента

        # Следующий POST идёт с cookie, но без заголовка X-Requested-With
        resp = await client.post("/auth/logout", headers={"X-Requested-With": ""} and {})
        assert resp.status_code == 403
        assert "X-Requested-With" in resp.json()["detail"]

    async def test_foreign_origin_rejected(self, make_client):
        client, _ = make_client
        resp = await client.post(
            "/auth/webapp-identify",
            json={"init_data": "hash=x"},
            headers={"X-Requested-With": "XMLHttpRequest",
                    "Origin": "https://evil.example.com"},
        )
        assert resp.status_code == 403

    async def test_get_requests_pass_without_headers(self, make_client):
        """Безопасные методы CSRF-guard не трогает."""
        client, _ = make_client
        resp = await client.get("/me")
        assert resp.status_code == 401  # дошёл до роута (нет токена), не 403
