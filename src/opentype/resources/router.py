from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional, Union

from ..types import (
    RouterCatalog,
    RouterModelFilters,
    RouterSelectResponse,
    RouterTaskTypesResponse,
    RouterWeights,
)
from ._shared import AsyncResource, SyncResource

Messages = Sequence[Mapping[str, str]]
Filters = Union[RouterModelFilters, Mapping[str, Any]]
Weights = Union[RouterWeights, Mapping[str, Optional[float]]]


def _plain(value: Union[Any, Mapping[str, Any]]) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump(exclude_none=True))
    return {k: v for k, v in value.items() if v is not None}


def select_body(
    prompt: Optional[str],
    messages: Optional[Messages],
    policy: Optional[str] = None,
    domain: Optional[str] = None,
    models: Optional[Filters] = None,
    *,
    task_type: Optional[str] = None,
    latency: Optional[str] = None,
    max_latency_ms: Optional[float] = None,
    weights: Optional[Weights] = None,
) -> dict[str, Any]:
    if (prompt is None) == (messages is None):
        raise ValueError("pass exactly one of prompt= or messages=")
    body: dict[str, Any] = {}
    if prompt is not None:
        body["prompt"] = prompt
    if messages is not None:
        body["messages"] = [dict(m) for m in messages]
    scalars = {
        "policy": policy,
        "domain": domain,
        "task_type": task_type,
        "latency": latency,
        "max_latency_ms": max_latency_ms,
    }
    body.update({k: v for k, v in scalars.items() if v is not None})
    if weights is not None:
        body["weights"] = _plain(weights)
    if models is not None:
        body["models"] = _plain(models)
    return body


class Router(SyncResource):
    def models(self) -> RouterCatalog:
        """``GET /v1/router/models``: the benchmark catalog."""
        return self._client._request(RouterCatalog, "GET", "/v1/router/models")

    def task_types(self) -> RouterTaskTypesResponse:
        """``GET /v1/router/task-types``: the task types the router classifies
        into, each with its benchmark weight vector. Free."""
        return self._client._request(RouterTaskTypesResponse, "GET", "/v1/router/task-types")

    def select(
        self,
        *,
        prompt: Optional[str] = None,
        messages: Optional[Messages] = None,
        policy: Optional[str] = None,
        domain: Optional[str] = None,
        task_type: Optional[str] = None,
        latency: Optional[str] = None,
        max_latency_ms: Optional[float] = None,
        weights: Optional[Weights] = None,
        models: Optional[Filters] = None,
    ) -> RouterSelectResponse:
        """``POST /v1/router/select``: which model to call for this task. Billed
        like a decision run (classification by Neon 1.1). Not auto-retried.

        ``task_type`` skips classification (see :meth:`task_types`) and wins over
        ``domain``. ``latency`` is ``interactive``, ``standard`` or ``batch``.
        ``weights`` (``quality``/``cost``/``speed``) needs ``policy="balanced"``
        or the default; otherwise the server answers ``400 weights_require_balanced``.
        """
        body = select_body(
            prompt,
            messages,
            policy,
            domain,
            models,
            task_type=task_type,
            latency=latency,
            max_latency_ms=max_latency_ms,
            weights=weights,
        )
        return self._client._request(RouterSelectResponse, "POST", "/v1/router/select", body=body)


class AsyncRouter(AsyncResource):
    async def models(self) -> RouterCatalog:
        return await self._client._request(RouterCatalog, "GET", "/v1/router/models")

    async def task_types(self) -> RouterTaskTypesResponse:
        return await self._client._request(RouterTaskTypesResponse, "GET", "/v1/router/task-types")

    async def select(
        self,
        *,
        prompt: Optional[str] = None,
        messages: Optional[Messages] = None,
        policy: Optional[str] = None,
        domain: Optional[str] = None,
        task_type: Optional[str] = None,
        latency: Optional[str] = None,
        max_latency_ms: Optional[float] = None,
        weights: Optional[Weights] = None,
        models: Optional[Filters] = None,
    ) -> RouterSelectResponse:
        body = select_body(
            prompt,
            messages,
            policy,
            domain,
            models,
            task_type=task_type,
            latency=latency,
            max_latency_ms=max_latency_ms,
            weights=weights,
        )
        return await self._client._request(RouterSelectResponse, "POST", "/v1/router/select", body=body)
