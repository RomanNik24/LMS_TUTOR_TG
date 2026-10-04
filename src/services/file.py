"""File service: S3 upload, presigned URLs."""

from typing: Optional
import uuid
from datetime: timedelta

from src.core.config import settings


class FileService:
    def __init__(self):
        # Initialize aioboto3 client
        pass

    async def upload_file(
        self,
        file_bytes: bytes,
        content_type: str,
        original_name: str,
        folder: str,
    ) -> str:
        """Upload file to S3, return s3_key."""
        # Validate MIME, size
        # Convert HEIC to JPEG if needed
        # Compress images
        # Generate UUID key
        ext = original_name.split(".")[-1].lower()
        s3_key = f"{folder}/{uuid.uuid4()}.{ext}"
        # Upload to S3
        return s3_key

    async def get_presigned_url(self, s3_key: str, ttl_seconds: int = 600) -> str:
        """Generate presigned URL for reading."""
        # Generate presigned GET URL
        return f"{settings.S3_PUBLIC_URL}/{s3_key}?signature=..."

    async def delete_file(self, s3_key: str) -> None:
        """Delete file from S3."""
        pass