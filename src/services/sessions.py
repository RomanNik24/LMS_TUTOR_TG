"""Серверные сессии Mini App в Redis + журнал аудита (docs/09 §2.2, §6).

Вместо долгоживущего JWT, который клиент хранит в памяти, Mini App получает
короткий случайный идентификатор сессии (cookie ``lms_session``). Токен
нельзя угадать (256 бит), сессию можно отозвать мгновенно (DEL по key), а
при компрометации достаточно очистить ``sess:*`` — все клиенты разлогинятся.

audit_log пишется в Redis-список ``audit:log`` (LPUSH/LTRIM): в MVP это
дешёвая, но честная запись чувствительных действий; на этапе PostgreSQL-схемы
из docs/04 его следует перенести в таблицу ``audit_log``.
"""

import hashlib
import json
import logging
import secrets
import time
from typing import Optional

from redis.asyncio import Redis

from src.core.redis import get_redis

logger = logging.getLogger(__name__)

SESSION_KEY_PREFIX = "sess:"
AUDIT_LOG_KEY = "audit:log"
AUDIT_LOG_MAX_ENTRIES = 10_000

# Срок жизни сессии Mini App: 30 дней неактивности для ученика,
# 7 дней для персонала (docs/09 §2.3).
SESSION_TTL_STUDENT_SECONDS = 30 * 24 * 3600
SESSION_TTL_STAFF_SECONDS = 7 * 24 * 3600


def _session_key(session_id: str) -> str:
    return SESSION_KEY_PREFIX + session_id


def hash_session_id(session_id: str) -> str:
    """SHA-256 от id сессии — для логов (сырой id в логи не попадает)."""
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


class SessionService:
    """Создание/проверка/отзыв серверных сессий в Redis."""

    def __init__(self, redis: Optional[Redis] = None):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis if self._redis is not None else get_redis()

    async def create(self, *, user_id: int, role: str) -> tuple[str, int]:
        """Создать сессию; вернуть (session_id, ttl_seconds)."""
        session_id = secrets.token_urlsafe(32)  # 256 бит случайности
        ttl = (
            SESSION_TTL_STAFF_SECONDS
            if role != "student"
            else SESSION_TTL_STUDENT_SECONDS
        )
        payload = json.dumps(
            {"user_id": user_id, "role": role, "created_at": int(time.time())}
        )
        await self.redis.set(_session_key(session_id), payload, ex=ttl)
        return session_id, ttl

    async def get(self, session_id: str) -> Optional[dict]:
        """Прочитать сессию и продлить TTL (скользящее истечение)."""
        if not session_id:
            return None
        key = _session_key(session_id)
        raw = await self.redis.get(key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self.redis.delete(key)
            return None
        ttl = (
            SESSION_TTL_STAFF_SECONDS
            if data.get("role") != "student"
            else SESSION_TTL_STUDENT_SECONDS
        )
        await self.redis.expire(key, ttl)
        return data

    async def revoke(self, session_id: str) -> None:
        """Выход: удалить конкретную сессию на сервере."""
        if session_id:
            await self.redis.delete(_session_key(session_id))

    async def revoke_all_for_user(self, user_id: int) -> int:
        """Отзыв всех сессий пользователя.

        Вызывается при архивации, смене telegram_id или роли (docs/09 §2.3),
        а также при инциденте безопасности.
        """
        deleted = 0
        async for key in self.redis.scan_iter(match=SESSION_KEY_PREFIX + "*",
                                               count=200):
            raw = await self.redis.get(key)
            if raw is None:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await self.redis.delete(key)
                continue
            if data.get("user_id") == user_id:
                await self.redis.delete(key)
                deleted += 1
        return deleted


async def write_audit(
    action: str,
    *,
    user_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip: Optional[str] = None,
) -> None:
    """Запись в журнал аудита (без персональных данных, только user_id).

    Ошибка записи не должна ронять бизнес-операцию — логируем и продолжаем.
    """
    entry = {
        "ts": int(time.time()),
        "action": action,
        "user_id": user_id,
        "ip": ip,
        "details": details or {},
    }
    try:
        redis = get_redis()
        pipe = redis.pipeline()
        pipe.lpush(AUDIT_LOG_KEY, json.dumps(entry, ensure_ascii=False))
        pipe.ltrim(AUDIT_LOG_KEY, 0, AUDIT_LOG_MAX_ENTRIES - 1)
        await pipe.execute()
    except Exception:  # noqa: BLE001 — аудит best-effort, не блокирует запрос
        logger.exception("Не удалось записать событие аудита: %s", action)


session_service = SessionService()

__all__ = [
    "SessionService",
    "session_service",
    "write_audit",
    "hash_session_id",
    "SESSION_KEY_PREFIX",
    "AUDIT_LOG_KEY",
]
