from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator, Mapping
from typing import Any, Optional, Union

import httpx

from .._base import cast_to, pending_error, transport_error
from .._exceptions import APIConnectionError, OpenTypeError
from .._pagination import AsyncPage, SyncPage
from .._streaming import aiter_events, iter_events
from ..types import RunEvent, RunListResponse, RunResponse
from ._shared import AsyncResource, SyncResource

CreateRunBody = Mapping[str, Any]
TERMINAL = ("completed", "failed")


def _body(body: Union[CreateRunBody, Any]) -> dict[str, Any]:
    if hasattr(body, "model_dump"):
        return body.model_dump(mode="json", by_alias=True, exclude_none=True)  # type: ignore[no-any-return]
    return {k: v for k, v in dict(body).items() if v is not None}


def _created(response: httpx.Response) -> RunResponse:
    run = cast_to(RunResponse, response)
    if response.status_code == 202:
        raise pending_error(response, run)
    return run


class Runs(SyncResource):
    def create(
        self,
        body: Union[CreateRunBody, Any],
        *,
        idempotency_key: Optional[str] = None,
        timeout: Union[float, httpx.Timeout, None] = None,
    ) -> RunResponse:
        """``POST /v1/runs``. Always sends an ``Idempotency-Key`` (yours, or a UUID).
        A ``202`` replay of an in-flight run raises ``RunPendingError``."""
        with self._client._send(
            "POST", "/v1/runs", body=_body(body), idempotency_key=idempotency_key, timeout=timeout
        ) as response:
            return _created(response)

    def get(self, run_id: str) -> RunResponse:
        return self._client._request(RunResponse, "GET", f"/v1/runs/{run_id}")

    def _page(self, limit: int, offset: int) -> RunListResponse:
        return self._client._request(RunListResponse, "GET", "/v1/runs", params={"limit": limit, "offset": offset})

    def list(self, *, limit: int = 20, offset: int = 0) -> SyncPage[RunResponse]:
        """Newest first. Iterating the result auto-paginates."""
        return SyncPage(self._page(limit, offset), self._page)

    def stream(self, run_id: str) -> Iterator[RunEvent]:
        """``state`` then (when terminal) ``terminal`` events. No resume."""
        with self._client._send(
            "GET", f"/v1/runs/{run_id}/stream", headers={"Accept": "text/event-stream"}, stream=True
        ) as response:
            try:
                yield from iter_events(response.iter_text())
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                raise transport_error(exc) from exc

    def wait_for(self, run_id: str, *, timeout: float = 170.0, poll_interval: float = 1.0) -> RunResponse:
        """Block until the run is terminal, then return it with its answer."""
        deadline = time.monotonic() + timeout
        while True:
            try:
                for event in self.stream(run_id):
                    if event.is_terminal:
                        return self.get(run_id)
            except APIConnectionError:
                pass
            run = self.get(run_id)
            if run.state in TERMINAL:
                return run
            if time.monotonic() >= deadline:
                raise OpenTypeError(f"run {run_id} not terminal after {timeout}s", code="wait_timeout")
            time.sleep(poll_interval)


class AsyncRuns(AsyncResource):
    async def create(
        self,
        body: Union[CreateRunBody, Any],
        *,
        idempotency_key: Optional[str] = None,
        timeout: Union[float, httpx.Timeout, None] = None,
    ) -> RunResponse:
        async with self._client._send(
            "POST", "/v1/runs", body=_body(body), idempotency_key=idempotency_key, timeout=timeout
        ) as response:
            return _created(response)

    async def get(self, run_id: str) -> RunResponse:
        return await self._client._request(RunResponse, "GET", f"/v1/runs/{run_id}")

    async def _page(self, limit: int, offset: int) -> RunListResponse:
        return await self._client._request(
            RunListResponse, "GET", "/v1/runs", params={"limit": limit, "offset": offset}
        )

    def list(self, *, limit: int = 20, offset: int = 0) -> AsyncPage[RunResponse]:
        """``await`` for the first page, or ``async for`` over every run."""
        return AsyncPage(self._page, limit, offset)

    async def stream(self, run_id: str) -> AsyncIterator[RunEvent]:
        async with self._client._send(
            "GET", f"/v1/runs/{run_id}/stream", headers={"Accept": "text/event-stream"}, stream=True
        ) as response:
            try:
                async for event in aiter_events(response.aiter_text()):
                    yield event
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                raise transport_error(exc) from exc

    async def wait_for(self, run_id: str, *, timeout: float = 170.0, poll_interval: float = 1.0) -> RunResponse:
        deadline = time.monotonic() + timeout
        while True:
            try:
                async for event in self.stream(run_id):
                    if event.is_terminal:
                        return await self.get(run_id)
            except APIConnectionError:
                pass
            run = await self.get(run_id)
            if run.state in TERMINAL:
                return run
            if time.monotonic() >= deadline:
                raise OpenTypeError(f"run {run_id} not terminal after {timeout}s", code="wait_timeout")
            await asyncio.sleep(poll_interval)
