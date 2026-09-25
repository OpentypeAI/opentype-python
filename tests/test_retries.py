from __future__ import annotations

import httpx
import pytest
import respx

from opentype import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenType,
    InsufficientCreditsError,
    InvalidRequestError,
    OpenType,
    RateLimitError,
    ServerError,
)
from opentype._base import retry_delay

from .conftest import BASE, err, run_json

DECISION = {"kind": "decision", "state": {}, "questions": {}, "max_output_tokens": 1}


def keys(route: respx.Route) -> list[str]:
    return [c.request.headers["idempotency-key"] for c in route.calls]


@respx.mock
def test_network_error_retries_with_same_key(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(
        side_effect=[httpx.ConnectError("boom"), httpx.ReadTimeout("slow"), httpx.Response(200, json=run_json())]
    )
    client.runs.create(DECISION)
    k = keys(route)
    assert len(k) == 3 and len(set(k)) == 1


@respx.mock
def test_5xx_retries_with_new_key(client: OpenType, _no_sleep: list[float]) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(
        side_effect=[
            httpx.Response(503, json=err("provider_unavailable")),
            httpx.Response(500, json=err("internal")),
            httpx.Response(200, json=run_json()),
        ]
    )
    client.runs.create(DECISION)
    k = keys(route)
    assert len(k) == 3 and len(set(k)) == 3
    assert len(_no_sleep) == 2 and all(0 <= d <= 2 for d in _no_sleep)


@respx.mock
def test_5xx_with_caller_key_is_not_retried(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(return_value=httpx.Response(503, json=err("provider_unavailable")))
    with pytest.raises(ServerError):
        client.runs.create(DECISION, idempotency_key="mine")
    assert route.call_count == 1


@respx.mock
def test_5xx_exhausts_retries(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(return_value=httpx.Response(504, json=err("deadline_exceeded")))
    with pytest.raises(ServerError) as exc:
        client.runs.create(DECISION)
    assert route.call_count == 3 and exc.value.code == "deadline_exceeded"


@respx.mock
def test_schema_violation_not_retried(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(
        return_value=httpx.Response(503, json=err("verdict_schema_violation", violations=["/risk"]))
    )
    with pytest.raises(ServerError) as exc:
        client.runs.create(DECISION)
    assert route.call_count == 1 and exc.value.violations == ["/risk"]


@pytest.mark.parametrize(
    ("status", "cls"),
    [(400, InvalidRequestError), (402, InsufficientCreditsError), (429, RateLimitError), (409, Exception)],
)
@respx.mock
def test_4xx_never_retried(client: OpenType, status: int, cls: type[Exception]) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(
        return_value=httpx.Response(status, json=err("x"), headers={"retry-after": "1"})
    )
    with pytest.raises(cls):
        client.runs.create(DECISION)
    assert route.call_count == 1


@respx.mock
def test_retry_after_respected(client: OpenType, _no_sleep: list[float]) -> None:
    respx.get(f"{BASE}/v1/quota").mock(
        side_effect=[httpx.Response(503, text="busy", headers={"retry-after": "3"}), httpx.Response(503, text="x")]
    )
    with pytest.raises(ServerError):
        OpenType(api_key="k", base_url=BASE, max_retries=1).usage.quota()
    assert _no_sleep == [3.0]


def test_backoff_bounds() -> None:
    for attempt, cap in [(0, 1), (1, 2), (2, 4), (5, 8)]:
        assert all(0 <= retry_delay(attempt, None) <= cap for _ in range(50))
    r = httpx.Response(503, headers={"retry-after-ms": "250"})
    assert retry_delay(0, r) == 0.25
    assert retry_delay(0, httpx.Response(503, headers={"retry-after": "9999"})) <= 1  # insane value ignored


@respx.mock
def test_get_retries_network_and_5xx(client: OpenType) -> None:
    route = respx.get(f"{BASE}/v1/runs/run_1").mock(
        side_effect=[
            httpx.ConnectError("x"),
            httpx.Response(502, text="bad gateway"),
            httpx.Response(200, json=run_json()),
        ]
    )
    assert client.runs.get("run_1").run_id == "run_1"
    assert route.call_count == 3
    assert "idempotency-key" not in route.calls.last.request.headers


@respx.mock
def test_plain_post_not_retried(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/keys/k/rotate").mock(side_effect=httpx.ConnectError("x"))
    with pytest.raises(APIConnectionError):
        client.keys.rotate("k")
    assert route.call_count == 1


@respx.mock
def test_max_retries_zero_and_timeout() -> None:
    route = respx.get(f"{BASE}/v1/billing").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(APITimeoutError) as exc:
        OpenType(api_key="k", base_url=BASE, max_retries=0).billing.get()
    assert route.call_count == 1 and exc.value.code == "timeout"
    assert isinstance(exc.value, APIConnectionError)


@respx.mock
async def test_async_same_key_then_new_key(aclient: AsyncOpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(
        side_effect=[
            httpx.ConnectError("x"),
            httpx.Response(500, json=err("internal")),
            httpx.Response(200, json=run_json()),
        ]
    )
    await aclient.runs.create(DECISION)
    k = keys(route)
    assert k[0] == k[1] and k[2] != k[1]


@respx.mock
async def test_async_402_not_retried(aclient: AsyncOpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(return_value=httpx.Response(402, json=err("insufficient_credits")))
    with pytest.raises(InsufficientCreditsError) as exc:
        await aclient.runs.create(DECISION)
    assert route.call_count == 1 and exc.value.code == "insufficient_credits"


@respx.mock
async def test_async_timeout() -> None:
    respx.get(f"{BASE}/v1/billing").mock(side_effect=httpx.ConnectTimeout("slow"))
    async with AsyncOpenType(api_key="k", base_url=BASE) as c:
        with pytest.raises(APITimeoutError):
            await c.billing.get()
    assert respx.calls.call_count == 3
