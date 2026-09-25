from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._client import AsyncOpenType, OpenType


class SyncResource:
    def __init__(self, client: OpenType) -> None:
        self._client = client


class AsyncResource:
    def __init__(self, client: AsyncOpenType) -> None:
        self._client = client
