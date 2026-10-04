"""Security utilities: token hashing, Telegram initData validation."""

import hashlib
import hmac
import secrets
from urllib.parse import parse_qsl

from src.core.config import settings


def generate_token(length: int = 32) -> str:
    """Generate URL-safe random token."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """SHA-256 hash of token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp initData.
    Returns parsed data dict if valid, None otherwise.
    """
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    # Sort and concatenate
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # Compute HMAC-SHA256 with bot token as key
    secret_key = hmac.new(
        b"WebAppData",
        settings.BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    # Check auth_date not older than 24 hours
    import time
    auth_date = int(parsed.get("auth_date", "0"))
    if time.time() - auth_date > 86400:
        return None

    return parsed


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    return hmac.compare_digest(a, b)
