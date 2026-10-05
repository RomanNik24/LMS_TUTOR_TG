"""Custom exception hierarchy."""

from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            f"{resource} not found",
            code="not_found",
            details={"resource": resource, "id": str(identifier)},
        )


class PermissionDeniedError(AppError):
    """Permission denied for action."""

    def __init__(self, action: str, resource: str | None = None):
        details = {"action": action}
        if resource:
            details["resource"] = resource
        super().__init__(
            f"Permission denied: {action}",
            code="permission_denied",
            details=details,
        )


class ValidationError(AppError):
    """Validation error."""

    def __init__(self, message: str, fields: dict[str, str] | None = None):
        super().__init__(
            message,
            code="validation_error",
            details={"fields": fields or {}},
        )


class ConflictError(AppError):
    """Resource conflict (e.g., duplicate)."""

    def __init__(self, message: str, resource: str | None = None):
        details = {}
        if resource:
            details["resource"] = resource
        super().__init__(message, code="conflict", details=details)


class BusinessRuleError(AppError):
    """Business rule violation."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code=code, details=details)


class ExternalServiceError(AppError):
    """External service error (Telegram, S3, etc.)."""

    def __init__(self, service: str, message: str):
        super().__init__(
            f"{service} error: {message}",
            code="external_service_error",
            details={"service": service},
        )


class UnauthorizedError(AppError):
    """Authentication required."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code="unauthenticated")


class RateLimitedError(AppError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            "Rate limit exceeded",
            code="rate_limited",
            details=details,
        )
