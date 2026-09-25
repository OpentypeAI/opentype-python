from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import respx

from opentype import AsyncOpenType, NotFoundError, OpenType, OpenTypeError
from opentype._streaming import SSEDecoder, iter_events

from .conftest import BASE, err, run_json

STATE = 'event: state\ndata: {"run_id":"run_1","state":"completed"}\n\n'
TERMINAL = (
    'event: terminal\ndata: {"run_id":"run_1","state":"completed","input_digest":"ab","output_digest":"cd",'
    '"kind":"decision","decision":{"answers":{"q":{"type":"noul","probability":0.7}}}}\n\n'
)


def test_decoder_basic() -> None:
    events = list(iter_events([STATE + TERMINAL]))
    assert [e.event for e in events] == ["state", "terminal"]
    assert events[0].state == "completed" and not events[0].is_terminal
    assert events[1].is_terminal and events[1].kind == "decision"
    assert events[1].decision is not None
    assert events[1].decision["answers"]["q"]["probability"] == 0.7


def test_decoder_split_chunks_crlf_and_comments() -> None:
    raw = (": keepalive\r\n" + STATE + TERMINAL).replace("\n", "\r\n")
    chunks = [raw[i : i + 3] for i in range(0, len(raw), 3)]
    events = list(iter_events(chunks))
    assert [e.event for e in events] == ["state", "terminal"]


def test_decoder_multiline_data_and_flush() -> None:
    d = SSEDecoder()
    assert d.feed('event: state\ndata: {"run_id":\ndata: "r"}') == []
    assert d.flush() == [("state", '{"run_id":\n"r"}')]


def test_decoder_bad_json() -> None:
    with pytest.raises(OpenTypeError):
        list(iter_events(["event: state\ndata: {nope\n\n"]))


@respx.mock
def test_stream_sync(client: OpenType) -> None:
    route = respx.get(f"{BASE}/v1/runs/run_1/stream").mock(
        return_value=httpx.Response(
            200, stream=_Chunks([STATE, TERMINAL[:20], TERMINAL[20:]]), headers={"content-type": "text/event-stream"}
        )
    )
    events = list(client.runs.stream("run_1"))
    assert [e.event for e in events] == ["state", "terminal"]
    assert route.calls.last.request.headers["accept"] == "text/event-stream"


@respx.mock
def test_stream_error_is_raised(client: OpenType) -> None:
    respx.get(f"{BASE}/v1/runs/nope/stream").mock(return_value=httpx.Response(404, json=err("run_not_found")))
    with pytest.raises(NotFoundError):
        list(client.runs.stream("nope"))


@respx.mock
def test_wait_for(client: OpenType) -> None:
    respx.get(f"{BASE}/v1/runs/run_1/stream").mock(return_value=httpx.Response(200, text=STATE + TERMINAL))
    respx.get(f"{BASE}/v1/runs/run_1").mock(return_value=httpx.Response(200, json=run_json()))
    assert client.runs.wait_for("run_1").state == "completed"


@respx.mock
async def test_stream_async(aclient: AsyncOpenType) -> None:
    respx.get(f"{BASE}/v1/runs/run_1/stream").mock(
        return_value=httpx.Response(200, stream=_AChunks([STATE[:7], STATE[7:] + TERMINAL]))
    )
    events = [e async for e in aclient.runs.stream("run_1")]
    assert [e.event for e in events] == ["state", "terminal"]


@respx.mock
async def test_wait_for_async_polls_when_not_terminal(aclient: AsyncOpenType) -> None:
    respx.get(f"{BASE}/v1/runs/run_1/stream").mock(
        return_value=httpx.Response(200, text='event: state\ndata: {"run_id":"run_1","state":"running"}\n\n')
    )
    respx.get(f"{BASE}/v1/runs/run_1").mock(
        side_effect=[httpx.Response(200, json=run_json(state="running")), httpx.Response(200, json=run_json())]
    )
    run = await aclient.runs.wait_for("run_1", poll_interval=0)
    assert run.state == "completed"


class _Chunks(httpx.SyncByteStream):
    def __init__(self, parts: list[str]) -> None:
        self.parts = parts

    def __iter__(self) -> Iterator[bytes]:
        for p in self.parts:
            yield p.encode()


class _AChunks(httpx.AsyncByteStream):
    def __init__(self, parts: list[str]) -> None:
        self.parts = parts

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for p in self.parts:
            yield p.encode()


class _Dropped(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield STATE.encode()
        raise httpx.RemoteProtocolError("peer closed")


@respx.mock
def test_dropped_stream_raises_sdk_error_and_wait_for_falls_back(client: OpenType) -> None:
    from opentype import APIConnectionError

    respx.get(f"{BASE}/v1/runs/run_1/stream").mock(side_effect=lambda req: httpx.Response(200, stream=_Dropped()))
    respx.get(f"{BASE}/v1/runs/run_1").mock(return_value=httpx.Response(200, json=run_json()))
    with pytest.raises(APIConnectionError):
        list(client.runs.stream("run_1"))
    assert client.runs.wait_for("run_1").state == "completed"
