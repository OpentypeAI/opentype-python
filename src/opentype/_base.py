"""Transport shared by the sync and async clients: auth, retries, idempotency."""

from __future__ import annotations

import asyncio
import email.utils
import json
import os
import platform
import random
import time
import uuid
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Optional, TypeVar, Union

import httpx
import pydantic

from ._exceptions import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenTypeError,
    RunPendingError,
    error_from_response,
)
from ._version import __version__

DEFAULT_BASE_URL = "https://api.opentype.dev"
# Above the 150 s cap on a long-context decision deadline (30 s + 120 s per
# 256k input tokens), so a slow run is never cut by the client.
DEFAULT_TIMEOUT = 170.0
DEFAULT_MAX_RETRIES = 2
MAX_RETRY_AFTER = 60.0

T = TypeVar("T")
Params = Mapping[str, Any]


class _Unset:
    pass


NOT_GIVEN: Any = _Unset()


def _retryable_status(response: httpx.Response) -> bool:
    return response.status_code in (500, 502, 503, 504)


def retry_after_seconds(response: Optional[httpx.Response]) -> Optional[float]:
    if response is None:
        return None
    raw = response.headers.get("retry-after-ms")
    if raw:
        try:
            return float(raw) / 1000.0
        except ValueError:
            pass
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        parsed = email.utils.parsedate_to_datetime(raw) if raw else None
        if parsed is None:
            return None
        return max(0.0, float(parsed.timestamp()) - time.time())


def retry_delay(attempt: int, response: Optional[httpx.Response]) -> float:
    """``Retry-After`` when the server sent a sane one, else 1, 2, 4 s with full jitter."""
    after = retry_after_seconds(response)
    if after is not None and 0 <= after <= MAX_RETRY_AFTER:
        return after
    return random.uniform(0, min(2.0**attempt, 8.0))


def _user_agent() -> str:
    return f"opentype-python/{__version__} python/{platform.python_version()}"


def _clean(params: Optional[Params]) -> Optional[dict[str, Any]]:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None and not isinstance(v, _Unset)}


def parse_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise OpenTypeError(
            f"expected JSON, got {response.headers.get('content-type', 'no content-type')}",
            code="invalid_response",
            status=response.status_code,
            request_id=response.headers.get("x-request-id"),
        ) from exc


def cast_to(model: type[T], response: httpx.Response) -> T:
    data = parse_json(response)
    if issubclass(model, pydantic.BaseModel):
        obj = model.model_validate(data)
        obj._request_id = response.headers.get("x-request-id")  # type: ignore[attr-defined]
        return obj
    return data  # type: ignore[no-any-return]


class _BaseClient:
    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: Union[str, httpx.URL, None],
        timeout: Union[float, httpx.Timeout, None],
        max_retries: int,
        default_headers: Optional[Mapping[str, str]],
    ) -> None:
        api_key = api_key or os.environ.get("OPENTYPE_API_KEY")
        if not api_key:
            raise OpenTypeError(
                "no API key: pass api_key= or set OPENTYPE_API_KEY",
                code="missing_credentials",
            )
        self.api_key = api_key
        self.base_url = httpx.URL(
            str(base_url or os.environ.get("OPENTYPE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/"
        )
        self.timeout: Union[float, httpx.Timeout] = DEFAULT_TIMEOUT if timeout is None else timeout
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.max_retries = max_retries
        self._default_headers = dict(default_headers or {})

    def _url(self, path: str) -> httpx.URL:
        return self.base_url.join(path.lstrip("/"))

    def _headers(self, extra: Optional[Mapping[str, str]], idempotency_key: Optional[str]) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": _user_agent(),
            **self._default_headers,
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _may_retry(method: str, idempotent: bool) -> bool:
        return idempotent or method.upper() in ("GET", "HEAD", "PUT", "DELETE")

    @staticmethod
    def _next_key(current: Optional[str], caller_key: bool) -> Optional[str]:
        # A 5xx may leave a failed run under the key; a new key is a new attempt.
        if current is None or caller_key:
            return current
        return str(uuid.uuid4())

    @staticmethod
    def _raise_for(response: httpx.Response, body_text: Optional[str] = None) -> None:
        if response.status_code >= 400:
            raise error_from_response(response, body_text)


class SyncAPIClient(_BaseClient):
    _client: httpx.Client

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Union[str, httpx.URL, None] = None,
        timeout: Union[float, httpx.Timeout, None] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=self.timeout)

    _sleep = staticmethod(time.sleep)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @contextmanager
    def _send(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Params] = None,
        body: Any = None,
        idempotency_key: Union[str, None, _Unset] = NOT_GIVEN,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Union[float, httpx.Timeout, None] = None,
        stream: bool = False,
    ) -> Iterator[httpx.Response]:
        """Send with retries; yields a successful response (body unread when ``stream``).

        ``idempotency_key``: ``NOT_GIVEN`` means the request carries none; ``None``
        means generate one; a string is the caller's own key."""
        caller_key = isinstance(idempotency_key, str)
        key: Optional[str]
        if isinstance(idempotency_key, _Unset):
            key = None
        else:
            key = idempotency_key or str(uuid.uuid4())
        may_retry = self._may_retry(method, key is not None)
        attempt = 0
        while True:
            request = self._client.build_request(
                method,
                self._url(path),
                params=_clean(params),
                content=None if body is None else json.dumps(body),
                headers={
                    **self._headers(headers, key),
                    **({"Content-Type": "application/json"} if body is not None else {}),
                },
                timeout=self.timeout if timeout is None else timeout,
            )
            try:
                response = self._client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                if may_retry and attempt < self.max_retries:
                    self._sleep(retry_delay(attempt, None))
                    attempt += 1
                    continue
                raise APITimeoutError() from exc
            except httpx.TransportError as exc:
                if may_retry and attempt < self.max_retries:
                    self._sleep(retry_delay(attempt, None))
                    attempt += 1
                    continue
                raise APIConnectionError(str(exc) or "connection error") from exc
            try:
                if response.status_code >= 400:
                    text = response.read().decode("utf-8", "replace")
                    err = error_from_response(response, text)
                    if (
                        may_retry
                        and attempt < self.max_retries
                        and _retryable_status(response)
                        and not (caller_key and key is not None)
                        and err.code != "verdict_schema_violation"
                    ):
                        delay = retry_delay(attempt, response)
                        response.close()
                        self._sleep(delay)
                        key = self._next_key(key, caller_key)
                        attempt += 1
                        continue
                    raise err
                if not stream:
                    response.read()
                yield response
                return
            finally:
                response.close()

    def _request(self, model: type[T], method: str, path: str, **kwargs: Any) -> T:
        with self._send(method, path, **kwargs) as response:
            return cast_to(model, response)


class AsyncAPIClient(_BaseClient):
    _client: httpx.AsyncClient

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Union[str, httpx.URL, None] = None,
        timeout: Union[float, httpx.Timeout, None] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.AsyncClient] = None,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=self.timeout)

    _sleep = staticmethod(asyncio.sleep)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self: T) -> T:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    @asynccontextmanager
    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Params] = None,
        body: Any = None,
        idempotency_key: Union[str, None, _Unset] = NOT_GIVEN,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Union[float, httpx.Timeout, None] = None,
        stream: bool = False,
    ) -> AsyncIterator[httpx.Response]:
        caller_key = isinstance(idempotency_key, str)
        key: Optional[str]
        if isinstance(idempotency_key, _Unset):
            key = None
        else:
            key = idempotency_key or str(uuid.uuid4())
        may_retry = self._may_retry(method, key is not None)
        attempt = 0
        while True:
            request = self._client.build_request(
                method,
                self._url(path),
                params=_clean(params),
                content=None if body is None else json.dumps(body),
                headers={
                    **self._headers(headers, key),
                    **({"Content-Type": "application/json"} if body is not None else {}),
                },
                timeout=self.timeout if timeout is None else timeout,
            )
            try:
                response = await self._client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                if may_retry and attempt < self.max_retries:
                    await self._sleep(retry_delay(attempt, None))
                    attempt += 1
                    continue
                raise APITimeoutError() from exc
            except httpx.TransportError as exc:
                if may_retry and attempt < self.max_retries:
                    await self._sleep(retry_delay(attempt, None))
                    attempt += 1
                    continue
                raise APIConnectionError(str(exc) or "connection error") from exc
            try:
                if response.status_code >= 400:
                    text = (await response.aread()).decode("utf-8", "replace")
                    err = error_from_response(response, text)
                    if (
                        may_retry
                        and attempt < self.max_retries
                        and _retryable_status(response)
                        and not (caller_key and key is not None)
                        and err.code != "verdict_schema_violation"
                    ):
                        delay = retry_delay(attempt, response)
                        await response.aclose()
                        await self._sleep(delay)
                        key = self._next_key(key, caller_key)
                        attempt += 1
                        continue
                    raise err
                if not stream:
                    await response.aread()
                yield response
                return
            finally:
                await response.aclose()

    async def _request(self, model: type[T], method: str, path: str, **kwargs: Any) -> T:
        async with self._send(method, path, **kwargs) as response:
            return cast_to(model, response)


def pending_error(response: httpx.Response, run: Any) -> RunPendingError:
    return RunPendingError(
        "a run with this Idempotency-Key is still in flight; poll it instead of resubmitting",
        run=run,
        code="run_pending",
        status=202,
        request_id=response.headers.get("x-request-id"),
        response=response,
    )


__all__ = ["APIStatusError", "AsyncAPIClient", "SyncAPIClient", "NOT_GIVEN"]
