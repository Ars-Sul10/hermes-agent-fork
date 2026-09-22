from __future__ import annotations
from typing import Any, Optional


class AqueraError(Exception):
    """Base exception for all Aquera API and integration errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(AqueraError):
    """Raised when authentication fails (HTTP 401: invalid or expired token)."""
    def __init__(self, message: str = "Aquera API credentials invalid or missing", details: Any = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(AqueraError):
    """Raised when user or client lacks permission (HTTP 403 / RBAC violation)."""
    def __init__(self, message: str = "User does not have permission for this action", details: Any = None):
        super().__init__(message, status_code=403, details=details)


class NotFoundError(AqueraError):
    """Raised when a requested resource is not found (HTTP 404)."""
    def __init__(self, message: str = "Resource not found in Aquera", details: Any = None):
        super().__init__(message, status_code=404, details=details)


class ValidationError(AqueraError):
    """Raised when payload or parameters fail business validation (HTTP 400 / 422)."""
    def __init__(self, message: str = "Input validation failed", details: Any = None):
        super().__init__(message, status_code=422, details=details)


class RateLimitError(AqueraError):
    """Raised when API rate limit is exceeded (HTTP 429)."""
    def __init__(self, message: str = "Aquera API rate limit exceeded. Please retry later.", details: Any = None):
        super().__init__(message, status_code=429, details=details)


class ServerError(AqueraError):
    """Raised when Aquera backend encounters an internal error (HTTP 5xx)."""
    def __init__(self, message: str = "Aquera server error", status_code: int = 500, details: Any = None):
        super().__init__(message, status_code=status_code, details=details)


class TimeoutError(AqueraError):
    """Raised when a request to Aquera times out."""
    def __init__(self, message: str = "Aquera API request timed out", details: Any = None):
        super().__init__(message, status_code=504, details=details)


def map_http_status_to_error(status_code: int, response_text: str) -> AqueraError:
    """Helper to convert HTTP status code to appropriate typed AqueraError."""
    # Sanitize message to never reveal sensitive headers or tokens
    sanitized_msg = response_text.replace("\n", " ").strip()
    if len(sanitized_msg) > 300:
        sanitized_msg = sanitized_msg[:300] + "..."

    if status_code == 401:
        return AuthenticationError(f"Aquera authentication failed: {sanitized_msg}")
    elif status_code == 403:
        return AuthorizationError(f"Aquera authorization denied: {sanitized_msg}")
    elif status_code == 404:
        return NotFoundError(f"Aquera resource not found: {sanitized_msg}")
    elif status_code in (400, 422):
        return ValidationError(f"Aquera validation error: {sanitized_msg}")
    elif status_code == 429:
        return RateLimitError(f"Aquera rate limited: {sanitized_msg}")
    elif status_code >= 500:
        return ServerError(f"Aquera backend server error: {sanitized_msg}", status_code=status_code)
    else:
        return AqueraError(f"Aquera API error ({status_code}): {sanitized_msg}", status_code=status_code)
