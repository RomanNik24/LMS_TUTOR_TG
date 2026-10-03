"""Верификация initData Telegram Mini App (docs/09 §1, §2.2).

Telegram подписывает строку запуска ``initData`` ключом, выведенным из токена
бота::

    secret_key = HMAC_SHA256(bot_token, "WebAppData")
    hash      = HMAC_SHA256(secret_key, data_check_string)

Проверяем:
- наличие обязательных полей (``init_hash``, ``auth_date``, ``user``);
- свежесть ``auth_date`` (не старше 24 часов);
- совпадение подписи (сравнение через ``hmac.compare_digest``).

Сырой ``telegram_id`` без подписи не принимается никогда — иначе любой, кто
знает чужой id, входит в его аккаунт.
"""

import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import parse_qsl

# Максимальный возраст initData (TTL подписи), сек. — docs/09 §2.2
MAX_AUTH_DATE_AGE_SECONDS = 24 * 3600

WEBAPP_DATA_KEY = b"WebAppData"


class InitDataError(ValueError):
    """initData отсутствует, повреждён, просрочен или подпись не совпала."""


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(WEBAPP_DATA_KEY, bot_token.encode("utf-8"),
                    hashlib.sha256).digest()


def build_check_string(init_data: dict) -> str:
    """data_check_string: отсортированные k=v (кроме hash/auth_date), через \\n."""
    items = sorted(
        (k, v) for k, v in init_data.items()
        if k not in {"hash", "auth_date"}
    )
    return "\n".join(f"{k}={v}" for k, v in items)


def verify_init_data(raw_init_data: str, bot_token: str) -> dict:
    """Проверить подпись initData и вернуть распарсенного пользователя.

    :param raw_init_data: строка ``initData`` из window.Telegram.WebApp
    :raises InitDataError: при любом несоответствии подписи/сроков.
    :return: dict c ключами telegram_id, username, first_name, auth_date.
    """
    if not raw_init_data or not bot_token:
        raise InitDataError("initData отсутствует")

    try:
        pairs = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    except ValueError as exc:  # некорректное URL-кодирование
        raise InitDataError(f"Некорректная строка initData: {exc}") from exc

    received_hash = pairs.get("hash")
    auth_date_raw = pairs.get("auth_date")
    user_raw = pairs.get("user")

    if not received_hash or not auth_date_raw or not user_raw:
        raise InitDataError("В initData нет обязательных полей hash/auth_date/user")

    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise InitDataError("auth_date не является числом") from exc

    if auth_date > time.time() + 300:
        raise InitDataError("auth_date из будущего")
    if time.time() - auth_date > MAX_AUTH_DATE_AGE_SECONDS:
        raise InitDataError("initData устарела (auth_date старше 24 часов)")

    check_string = build_check_string(pairs)
    expected = hmac.new(_secret_key(bot_token), check_string.encode("utf-8"),
                        hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("Подпись initData не подтверждена (bad hash)")

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InitDataError("Поле user в initData не является JSON") from exc

    telegram_id = user.get("id")
    if not isinstance(telegram_id, int):
        raise InitDataError("В initData нет корректного user.id")

    return {
        "telegram_id": telegram_id,
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "auth_date": auth_date,
    }


def extract_telegram_id_from_init_data(
    raw_init_data: Optional[str],
    bot_token: str,
) -> int:
    """Удобная обёртка: верификация + только telegram_id.

    :raises InitDataError: подпись не пройдена;
    :raises LookupError: пользователь в системе не найден (проверяет вызывающий код).
    """
    if not raw_init_data:
        raise InitDataError("initData не передана")
    return verify_init_data(raw_init_data, bot_token)["telegram_id"]
