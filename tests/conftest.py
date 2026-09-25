from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest

from opentype import AsyncOpenType, OpenType, _base

BASE = "https://api.test"


def run_json(run_id: str = "run_1", state: str = "completed", **extra: Any) -> dict[str, Any]:
    return {"run_id": run_id, "kind": "decision", "state": state, "input_digest": "ab", "replayed": False, **extra}


def err(code: str, message: str = "nope", **extra: Any) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": "req_1", **extra}}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []

    async def asleep(d: float) -> None:
        slept.append(d)

    monkeypatch.setattr(_base.SyncAPIClient, "_sleep", staticmethod(slept.append))
    monkeypatch.setattr(_base.AsyncAPIClient, "_sleep", staticmethod(asleep))
    return slept


@pytest.fixture
def client() -> Iterator[OpenType]:
    with OpenType(api_key="otsk_test", base_url=BASE) as c:
        yield c


@pytest.fixture
async def aclient() -> AsyncIterator[AsyncOpenType]:
    async with AsyncOpenType(api_key="otsk_test", base_url=BASE) as c:
        yield c
