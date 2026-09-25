from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Iterator
from typing import Callable, Generic, Optional, TypeVar

from .types import RunListResponse, RunResponse

T = TypeVar("T")


class SyncPage(Generic[T]):
    """One page of runs. Iterating it walks every later page too (offset paging);
    use ``.data`` for this page only."""

    def __init__(self, page: RunListResponse, fetch: Callable[[int, int], RunListResponse]) -> None:
        self._page = page
        self._fetch = fetch

    @property
    def data(self) -> list[RunResponse]:
        return list(self._page.runs)

    def has_next_page(self) -> bool:
        return len(self._page.runs) > 0 and len(self._page.runs) >= self._page.limit

    def get_next_page(self) -> Optional[SyncPage[T]]:
        if not self.has_next_page():
            return None
        nxt = self._fetch(self._page.limit, self._page.offset + len(self._page.runs))
        return SyncPage(nxt, self._fetch)

    def iter_pages(self) -> Iterator[SyncPage[T]]:
        page: Optional[SyncPage[T]] = self
        while page is not None:
            yield page
            page = page.get_next_page()

    def __iter__(self) -> Iterator[RunResponse]:
        for page in self.iter_pages():
            yield from page._page.runs


class AsyncPage(Generic[T]):
    """Awaitable for the first page; ``async for`` walks every page."""

    def __init__(self, fetch: Callable[[int, int], Awaitable[RunListResponse]], limit: int, offset: int) -> None:
        self._fetch = fetch
        self._limit = limit
        self._offset = offset

    def __await__(self):  # type: ignore[no-untyped-def]
        return self._fetch(self._limit, self._offset).__await__()

    async def __aiter__(self) -> AsyncIterator[RunResponse]:
        limit, offset = self._limit, self._offset
        while True:
            page = await self._fetch(limit, offset)
            for run in page.runs:
                yield run
            if not page.runs or len(page.runs) < page.limit:
                return
            limit, offset = page.limit, page.offset + len(page.runs)
