from __future__ import annotations

from typing import Optional

from ..types import BillingResponse, CheckoutResponse, PortalResponse
from ._shared import AsyncResource, SyncResource


def _recharge(enabled: bool, threshold_micros: Optional[int], amount_micros: Optional[int]) -> dict[str, object]:
    body: dict[str, object] = {"enabled": enabled}
    if threshold_micros is not None:
        body["threshold_micros"] = threshold_micros
    if amount_micros is not None:
        body["amount_micros"] = amount_micros
    return body


class Billing(SyncResource):
    def get(self) -> BillingResponse:
        return self._client._request(BillingResponse, "GET", "/v1/billing")

    def set_auto_recharge(
        self, *, enabled: bool, threshold_micros: Optional[int] = None, amount_micros: Optional[int] = None
    ) -> BillingResponse:
        body = _recharge(enabled, threshold_micros, amount_micros)
        return self._client._request(BillingResponse, "PUT", "/v1/billing/auto-recharge", body=body)

    def checkout(self, *, amount_micros: int) -> CheckoutResponse:
        """Returns a hosted checkout URL. Not retried (POST without idempotency)."""
        return self._client._request(
            CheckoutResponse, "POST", "/v1/billing/checkout", body={"amount_micros": amount_micros}
        )

    def portal(self) -> PortalResponse:
        return self._client._request(PortalResponse, "POST", "/v1/billing/portal")


class AsyncBilling(AsyncResource):
    async def get(self) -> BillingResponse:
        return await self._client._request(BillingResponse, "GET", "/v1/billing")

    async def set_auto_recharge(
        self, *, enabled: bool, threshold_micros: Optional[int] = None, amount_micros: Optional[int] = None
    ) -> BillingResponse:
        body = _recharge(enabled, threshold_micros, amount_micros)
        return await self._client._request(BillingResponse, "PUT", "/v1/billing/auto-recharge", body=body)

    async def checkout(self, *, amount_micros: int) -> CheckoutResponse:
        return await self._client._request(
            CheckoutResponse, "POST", "/v1/billing/checkout", body={"amount_micros": amount_micros}
        )

    async def portal(self) -> PortalResponse:
        return await self._client._request(PortalResponse, "POST", "/v1/billing/portal")
