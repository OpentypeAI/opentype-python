from __future__ import annotations

import httpx
import respx

from opentype import AsyncOpenType, OpenType

from .conftest import BASE, run_json


def _pages(route: respx.Route, total: int, limit: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        lim = int(request.url.params["limit"])
        off = int(request.url.params["offset"])
        runs = [run_json(f"run_{i}") for i in range(off, min(off + lim, total))]
        return httpx.Response(200, json={"runs": runs, "limit": lim, "offset": off})

    route.mock(side_effect=handler)


@respx.mock
def test_auto_paginate(client: OpenType) -> None:
    route = respx.get(f"{BASE}/v1/runs")
    _pages(route, total=5, limit=2)
    page = client.runs.list(limit=2)
    assert [r.run_id for r in page.data] == ["run_0", "run_1"]
    assert [r.run_id for r in page] == [f"run_{i}" for i in range(5)]
    offsets = [c.request.url.params["offset"] for c in route.calls]
    assert offsets == ["0", "2", "4"]  # first page is reused, not refetched


@respx.mock
def test_exact_multiple_stops_on_empty(client: OpenType) -> None:
    route = respx.get(f"{BASE}/v1/runs")
    _pages(route, total=4, limit=2)
    assert len(list(client.runs.list(limit=2))) == 4
    assert route.call_count == 3  # 0, 2, then an empty page at 4


@respx.mock
def test_server_clamps_limit(client: OpenType) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        off = int(request.url.params["offset"])
        runs = [run_json(f"run_{i}") for i in range(off, min(off + 100, 150))]
        return httpx.Response(200, json={"runs": runs, "limit": 100, "offset": off})

    respx.get(f"{BASE}/v1/runs").mock(side_effect=handler)
    page = client.runs.list(limit=1000)
    assert page.has_next_page()
    assert len(list(page)) == 150
    nxt = page.get_next_page()
    assert nxt is not None and not nxt.has_next_page()


@respx.mock
async def test_async_paginate(aclient: AsyncOpenType) -> None:
    _pages(respx.get(f"{BASE}/v1/runs"), total=3, limit=2)
    first = await aclient.runs.list(limit=2)
    assert len(first.runs) == 2
    assert [r.run_id async for r in aclient.runs.list(limit=2)] == ["run_0", "run_1", "run_2"]
