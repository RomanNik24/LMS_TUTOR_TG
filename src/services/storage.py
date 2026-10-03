"""Хранилище загруженных файлов ДЗ (docs/09 §4).

Абстракция нужна, чтобы заменить локальную заглушку на приватный бакет
S3/MinIO с presigned URL, не трогая слой API. Выдача файла — только через
эндпоинт с проверкой прав: публичная статика /uploads удалена из приложения.
"""

import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)

# owner/<uuid><ext> — путь формирует только сервер, пользовательское имя файла
# в него никогда не попадает.
_FILE_KEY_RE = re.compile(r"^(\d+)/([0-9a-f]{32}\.[a-z0-9]{1,8})$")


class FileStorageError(Exception):
    """Файл не найден или ключ некорректен."""


def build_key(owner_id: int, ext: str) -> str:
    """Сгенерировать ключ хранилища: <owner_id>/<uuid4hex><.ext>."""
    return f"{owner_id}/{uuid.uuid4().hex}{ext}"


def parse_owner(key: str) -> Optional[int]:
    """Извлечь id владельца из ключа (для проверки прав при отдаче)."""
    match = _FILE_KEY_RE.match(key.lstrip("/"))
    if not match:
        return None
    return int(match.group(1))


class LocalFileStorage:
    """Локальная реализация (dev/MVP). В проде заменяется на S3Storage.

    Ключ == относительный путь внутри settings.upload_dir; владелец кодируется
    первым сегментом пути, что даёт дешёвую проверку прав без отдельной таблицы.
    """

    def __init__(self, root: Optional[str] = None):
        self.root = Path(root or settings.upload_dir)

    def save(self, key: str, content: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.info("saved upload %s (%d bytes)", key, len(content))
        return key

    def read(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise FileStorageError(f"Файл не найден: {key}")
        return path.read_bytes()

    def content_type(self, key: str) -> str:
        ext = Path(key).suffix.lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
            ".txt": "text/plain; charset=utf-8",
            ".docx": "application/vnd.openxmlformats-officedocument"
                     ".wordprocessingml.document",
            ".zip": "application/zip",
        }.get(ext, "application/octet-stream")

    def _resolve(self, key: str) -> Path:
        """Безопасное разрешение ключа: никаких `..` и абсолютных путей."""
        if not key or key.startswith("/") or "\\" in key:
            raise FileStorageError("Некорректный ключ файла")
        path = (self.root / key).resolve()
        root = self.root.resolve()
        if not str(path).startswith(str(root) + "/"):
            raise FileStorageError("Некорректный ключ файла")
        return path


# Единая точка доступа к хранилищу. При переходе на S3 здесь появится
# выбор реализации по настройкам (S3_BUCKET и т.п.).
storage = LocalFileStorage()
