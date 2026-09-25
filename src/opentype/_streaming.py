"""Server-sent events for ``GET /v1/runs/{id}/stream``.

The server sends ``event: state`` then, once the run is terminal,
``event: terminal``; each ``data:`` line is one JSON object. There is no resume
(no ``id:``), so a dropped stream is recovered with ``runs.get``."""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from typing import Any, Optional

from ._exceptions import OpenTypeError
from .types import RunEvent


class SSEDecoder:
    """Incremental decoder: feed text chunks, get ``(event, data)`` pairs."""

    def __init__(self) -> None:
        self._buffer = ""
        self._event: Optional[str] = None
        self._data: list[str] = []

    def feed(self, chunk: str) -> list[tuple[str, str]]:
        self._buffer += chunk
        out: list[tuple[str, str]] = []
        while True:
            idx = self._buffer.find("\n")
            if idx < 0:
                break
            line = self._buffer[:idx].rstrip("\r")
            self._buffer = self._buffer[idx + 1 :]
            frame = self._line(line)
            if frame is not None:
                out.append(frame)
        return out

    def flush(self) -> list[tuple[str, str]]:
        out = self.feed("\n") if self._buffer else []
        frame = self._line("")
        if frame is not None:
            out.append(frame)
        return out

    def _line(self, line: str) -> Optional[tuple[str, str]]:
        if line == "":
            if not self._data and self._event is None:
                return None
            frame = (self._event or "message", "\n".join(self._data))
            self._event, self._data = None, []
            return frame
        if line.startswith(":"):
            return None
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            self._event = value
        elif field == "data":
            self._data.append(value)
        return None


def _to_event(event: str, data: str) -> RunEvent:
    try:
        payload: Any = json.loads(data) if data else {}
    except ValueError as exc:
        raise OpenTypeError(f"malformed SSE data for event {event!r}", code="invalid_response") from exc
    if not isinstance(payload, dict):
        payload = {"data": payload}
    return RunEvent.model_validate({"event": event, **payload})


def iter_events(chunks: Iterable[str]) -> Iterator[RunEvent]:
    decoder = SSEDecoder()
    for chunk in chunks:
        for event, data in decoder.feed(chunk):
            yield _to_event(event, data)
    for event, data in decoder.flush():
        yield _to_event(event, data)


async def aiter_events(chunks: AsyncIterable[str]) -> AsyncIterator[RunEvent]:
    decoder = SSEDecoder()
    async for chunk in chunks:
        for event, data in decoder.feed(chunk):
            yield _to_event(event, data)
    for event, data in decoder.flush():
        yield _to_event(event, data)
