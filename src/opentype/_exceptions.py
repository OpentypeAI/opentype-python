from __future__ import annotations

from typing import Any, Optional

import httpx

__all__ = [
    "OpenTypeError",
    "APIStatusError",
    "APIConnectionError",
    "APITimeoutError",
    "AuthenticationError",
    "PermissionDeniedError",
    "InsufficientCreditsError",
    "RateLimitError",
    "InvalidRequestError",
    "NotFoundError",
    "ConflictError",
    "ServerError",
    "RunPendingError",
    "BadRequestError",
    "QuotaExceededError",
    "InternalServerError",
]


class OpenTypeError(Exception):
    """Base of every error the SDK raises. Branch on ``code``, never on ``message``."""

    code: str
    message: str
    request_id: Optional[str]
    status: Optional[int]
    violations: Optional[list[str]]
    #: The ``Idempotency-Key`` the failed request sent, when it sent one. Send the
    #: same request again with this key to replay a run or classification that may
    #: already have been charged instead of paying for a new one.
    idempotency_key: Optional[str] = None

    def __init__(
        self,
        message: str,
        *,
        code: str = "opentype_error",
        request_id: Optional[str] = None,
        status: Optional[int] = None,
        violations: Optional[list[str]] = None,
        body: Any = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.status = status
        self.violations = violations
        self.body = body
        self.response = response

    def __str__(self) -> str:
        parts = [f"{self.code}: {self.message}"]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " ".join(parts)


class APIStatusError(OpenTypeError):
    """The server answered with an error status."""

    status: int


class InvalidRequestError(APIStatusError):
    """400 and 413: the request itself is wrong. Not retried."""


class AuthenticationError(APIStatusError):
    """401: missing or invalid credential."""


class InsufficientCreditsError(APIStatusError):
    """402: the balance cannot cover the run."""


class PermissionDeniedError(APIStatusError):
    """403: the key lacks a scope, or the route is session-only."""


class NotFoundError(APIStatusError):
    """404."""


class ConflictError(APIStatusError):
    """409: e.g. ``idempotency_conflict`` (same key, different body)."""


class RateLimitError(APIStatusError):
    """429: rate, spend or token quota. Never retried automatically."""


class ServerError(APIStatusError):
    """5xx. ``verdict_schema_violation`` (503) carries ``violations``."""


class RunPendingError(APIStatusError):
    """202 on a replayed ``Idempotency-Key``: the original run is still in flight.

    ``run`` holds the in-flight run; poll it with ``runs.get`` / ``runs.wait_for``
    instead of resubmitting."""

    def __init__(self, message: str, *, run: Any, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.run = run


class APIConnectionError(OpenTypeError):
    """No response: DNS, TCP, TLS or a dropped connection."""

    def __init__(self, message: str = "connection error", *, code: str = "connection_error") -> None:
        super().__init__(message, code=code)


class APITimeoutError(APIConnectionError):
    """The request exceeded the client timeout."""

    def __init__(self, message: str = "request timed out") -> None:
        super().__init__(message, code="timeout")


# Aliases matching the finer-grained names used in the TypeScript SDK docs.
BadRequestError = InvalidRequestError
QuotaExceededError = RateLimitError
InternalServerError = ServerError

_BY_STATUS: dict[int, type[APIStatusError]] = {
    400: InvalidRequestError,
    401: AuthenticationError,
    402: InsufficientCreditsError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    413: InvalidRequestError,
    422: InvalidRequestError,
    429: RateLimitError,
}


def error_from_response(response: httpx.Response, body_text: Optional[str] = None) -> APIStatusError:
    """Map an error response to its class. JSON envelopes are
    ``{"error": {code, message, request_id, violations?}}``; plain-text bodies
    map to code ``http_<status>``."""
    status = response.status_code
    text = body_text if body_text is not None else response.text
    request_id = response.headers.get("x-request-id")
    code = f"http_{status}"
    message = text.strip() or response.reason_phrase or f"HTTP {status}"
    violations: Optional[list[str]] = None
    body: Any = text
    try:
        import json

        body = json.loads(text)
    except ValueError:
        pass
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        err = body["error"]
        code = str(err.get("code") or code)
        message = str(err.get("message") or message)
        request_id = err.get("request_id") or request_id
        raw = err.get("violations")
        if isinstance(raw, list):
            violations = [str(v) for v in raw]
    cls = _BY_STATUS.get(status) or (ServerError if status >= 500 else APIStatusError)
    return cls(
        message,
        code=code,
        request_id=request_id,
        status=status,
        violations=violations,
        body=body,
        response=response,
    )
