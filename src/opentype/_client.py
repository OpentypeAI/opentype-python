from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional, Union

import httpx

from ._base import DEFAULT_MAX_RETRIES, AsyncAPIClient, SyncAPIClient
from .resources import (
    AsyncBilling,
    AsyncKeys,
    AsyncRouter,
    AsyncRuns,
    AsyncUsage,
    Billing,
    Keys,
    Router,
    Runs,
    Usage,
)
from .resources.router import Filters, Messages, Weights
from .types import RouterSelectResponse, RunResponse

# Decisions emit a handful of tokens; the value bounds the spend estimate.
DEFAULT_DECISION_MAX_OUTPUT_TOKENS = 64


def decision_body(
    *,
    state: Any,
    questions: Mapping[str, Any],
    instructions: Optional[str],
    question_order: Optional[Sequence[str]],
    draws: Optional[int],
    think_tokens: Optional[int],
    model: Optional[str],
    max_output_tokens: int,
    deadline_ms: Optional[int],
) -> dict[str, Any]:
    return {
        "kind": "decision",
        "state": state,
        "questions": dict(questions),
        "instructions": instructions,
        "question_order": list(question_order) if question_order is not None else None,
        "draws": draws,
        "think_tokens": think_tokens,
        "model": model,
        "max_output_tokens": max_output_tokens,
        "deadline_ms": deadline_ms,
    }


def verdict_body(
    *,
    messages: Messages,
    schema: Mapping[str, Any],
    max_output_tokens: int,
    system: Optional[str],
    deadline_ms: Optional[int],
    capability_hint: Optional[Sequence[str]],
) -> dict[str, Any]:
    return {
        "kind": "verdict",
        "messages": [dict(m) for m in messages],
        "schema": dict(schema),
        "system": system,
        "max_output_tokens": max_output_tokens,
        "deadline_ms": deadline_ms,
        "capability_hint": list(capability_hint) if capability_hint is not None else None,
    }


class OpenType(SyncAPIClient):
    """Synchronous OpenType client.

    ``api_key`` defaults to ``OPENTYPE_API_KEY``; ``base_url`` to
    ``OPENTYPE_BASE_URL`` or ``https://api.opentype.dev``."""

    runs: Runs
    usage: Usage
    billing: Billing
    keys: Keys
    router: Router

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
            http_client=http_client,
            default_headers=default_headers,
        )
        self.runs = Runs(self)
        self.usage = Usage(self)
        self.billing = Billing(self)
        self.keys = Keys(self)
        self.router = Router(self)

    def decide(
        self,
        *,
        state: Any,
        questions: Mapping[str, Any],
        instructions: Optional[str] = None,
        question_order: Optional[Sequence[str]] = None,
        draws: Optional[int] = None,
        think_tokens: Optional[int] = None,
        model: Optional[str] = None,
        max_output_tokens: int = DEFAULT_DECISION_MAX_OUTPUT_TOKENS,
        deadline_ms: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> RunResponse:
        """A decision run: probabilities per question, answered by Neon 1.1."""
        body = decision_body(
            state=state,
            questions=questions,
            instructions=instructions,
            question_order=question_order,
            draws=draws,
            think_tokens=think_tokens,
            model=model,
            max_output_tokens=max_output_tokens,
            deadline_ms=deadline_ms,
        )
        return self.runs.create(body, idempotency_key=idempotency_key)

    def verdict(
        self,
        *,
        messages: Messages,
        schema: Mapping[str, Any],
        max_output_tokens: int,
        system: Optional[str] = None,
        deadline_ms: Optional[int] = None,
        capability_hint: Optional[Sequence[str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> RunResponse:
        """A verdict run: a JSON document validated against ``schema``."""
        body = verdict_body(
            messages=messages,
            schema=schema,
            max_output_tokens=max_output_tokens,
            system=system,
            deadline_ms=deadline_ms,
            capability_hint=capability_hint,
        )
        return self.runs.create(body, idempotency_key=idempotency_key)

    def route(
        self,
        prompt: Optional[str] = None,
        *,
        messages: Optional[Messages] = None,
        policy: Optional[str] = None,
        domain: Optional[str] = None,
        task_type: Optional[str] = None,
        latency: Optional[str] = None,
        max_latency_ms: Optional[float] = None,
        weights: Optional[Weights] = None,
        models: Optional[Filters] = None,
    ) -> RouterSelectResponse:
        """Shorthand for ``router.select``: ``client.route("...").model.id``."""
        return self.router.select(
            prompt=prompt,
            messages=messages,
            policy=policy,
            domain=domain,
            task_type=task_type,
            latency=latency,
            max_latency_ms=max_latency_ms,
            weights=weights,
            models=models,
        )


class AsyncOpenType(AsyncAPIClient):
    """Asynchronous OpenType client; same surface as :class:`OpenType`."""

    runs: AsyncRuns
    usage: AsyncUsage
    billing: AsyncBilling
    keys: AsyncKeys
    router: AsyncRouter

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
            http_client=http_client,
            default_headers=default_headers,
        )
        self.runs = AsyncRuns(self)
        self.usage = AsyncUsage(self)
        self.billing = AsyncBilling(self)
        self.keys = AsyncKeys(self)
        self.router = AsyncRouter(self)

    async def decide(
        self,
        *,
        state: Any,
        questions: Mapping[str, Any],
        instructions: Optional[str] = None,
        question_order: Optional[Sequence[str]] = None,
        draws: Optional[int] = None,
        think_tokens: Optional[int] = None,
        model: Optional[str] = None,
        max_output_tokens: int = DEFAULT_DECISION_MAX_OUTPUT_TOKENS,
        deadline_ms: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> RunResponse:
        body = decision_body(
            state=state,
            questions=questions,
            instructions=instructions,
            question_order=question_order,
            draws=draws,
            think_tokens=think_tokens,
            model=model,
            max_output_tokens=max_output_tokens,
            deadline_ms=deadline_ms,
        )
        return await self.runs.create(body, idempotency_key=idempotency_key)

    async def verdict(
        self,
        *,
        messages: Messages,
        schema: Mapping[str, Any],
        max_output_tokens: int,
        system: Optional[str] = None,
        deadline_ms: Optional[int] = None,
        capability_hint: Optional[Sequence[str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> RunResponse:
        body = verdict_body(
            messages=messages,
            schema=schema,
            max_output_tokens=max_output_tokens,
            system=system,
            deadline_ms=deadline_ms,
            capability_hint=capability_hint,
        )
        return await self.runs.create(body, idempotency_key=idempotency_key)

    async def route(
        self,
        prompt: Optional[str] = None,
        *,
        messages: Optional[Messages] = None,
        policy: Optional[str] = None,
        domain: Optional[str] = None,
        task_type: Optional[str] = None,
        latency: Optional[str] = None,
        max_latency_ms: Optional[float] = None,
        weights: Optional[Weights] = None,
        models: Optional[Filters] = None,
    ) -> RouterSelectResponse:
        return await self.router.select(
            prompt=prompt,
            messages=messages,
            policy=policy,
            domain=domain,
            task_type=task_type,
            latency=latency,
            max_latency_ms=max_latency_ms,
            weights=weights,
            models=models,
        )
