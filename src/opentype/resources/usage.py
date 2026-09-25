from __future__ import annotations

from typing import Optional

from ..types import (
    DailyUsageResponse,
    LedgerResponse,
    OrganizationUsageResponse,
    QuotaResponse,
    RunUsageResponse,
)
from ._shared import AsyncResource, SyncResource


def _window(start_at: Optional[str], end_at: Optional[str]) -> dict[str, Optional[str]]:
    return {"start_at": start_at, "end_at": end_at}


class Usage(SyncResource):
    """Window bounds are RFC 3339 and must be given together; omitted means the
    current quota period."""

    def summary(self, *, start_at: Optional[str] = None, end_at: Optional[str] = None) -> OrganizationUsageResponse:
        return self._client._request(OrganizationUsageResponse, "GET", "/v1/usage", params=_window(start_at, end_at))

    def daily(self, *, start_at: Optional[str] = None, end_at: Optional[str] = None) -> DailyUsageResponse:
        return self._client._request(DailyUsageResponse, "GET", "/v1/usage/daily", params=_window(start_at, end_at))

    def ledger(
        self, *, start_at: Optional[str] = None, end_at: Optional[str] = None, limit: Optional[int] = None
    ) -> LedgerResponse:
        params = {**_window(start_at, end_at), "limit": limit}
        return self._client._request(LedgerResponse, "GET", "/v1/usage/ledger", params=params)

    def run(self, run_id: str) -> RunUsageResponse:
        return self._client._request(RunUsageResponse, "GET", f"/v1/usage/runs/{run_id}")

    def quota(self) -> QuotaResponse:
        return self._client._request(QuotaResponse, "GET", "/v1/quota")


class AsyncUsage(AsyncResource):
    async def summary(
        self, *, start_at: Optional[str] = None, end_at: Optional[str] = None
    ) -> OrganizationUsageResponse:
        return await self._client._request(
            OrganizationUsageResponse, "GET", "/v1/usage", params=_window(start_at, end_at)
        )

    async def daily(self, *, start_at: Optional[str] = None, end_at: Optional[str] = None) -> DailyUsageResponse:
        return await self._client._request(
            DailyUsageResponse, "GET", "/v1/usage/daily", params=_window(start_at, end_at)
        )

    async def ledger(
        self, *, start_at: Optional[str] = None, end_at: Optional[str] = None, limit: Optional[int] = None
    ) -> LedgerResponse:
        params = {**_window(start_at, end_at), "limit": limit}
        return await self._client._request(LedgerResponse, "GET", "/v1/usage/ledger", params=params)

    async def run(self, run_id: str) -> RunUsageResponse:
        return await self._client._request(RunUsageResponse, "GET", f"/v1/usage/runs/{run_id}")

    async def quota(self) -> QuotaResponse:
        return await self._client._request(QuotaResponse, "GET", "/v1/quota")
