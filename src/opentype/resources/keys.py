from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

from ..types import KeyListResponse, KeyResponse, KeyWithSecretResponse
from ._shared import AsyncResource, SyncResource


def _create_body(name: str, scopes: Sequence[str], principal: Optional[Any]) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name, "scopes": list(scopes)}
    if principal is not None:
        body["principal"] = principal
    return body


class Keys(SyncResource):
    def list(self) -> KeyListResponse:
        return self._client._request(KeyListResponse, "GET", "/v1/keys")

    def get(self, key_id: str) -> KeyResponse:
        return self._client._request(KeyResponse, "GET", f"/v1/keys/{key_id}")

    def revoke(self, key_id: str) -> KeyResponse:
        """Idempotent: revoking a revoked key returns it unchanged."""
        return self._client._request(KeyResponse, "DELETE", f"/v1/keys/{key_id}")

    def rotate(self, key_id: str) -> KeyWithSecretResponse:
        """New secret, shown once. Not retried: a lost response means rotate again."""
        return self._client._request(KeyWithSecretResponse, "POST", f"/v1/keys/{key_id}/rotate")

    def create(self, *, name: str, scopes: Sequence[str], principal: Optional[Any] = None) -> KeyWithSecretResponse:
        """Console-session only: an API-key caller gets ``PermissionDeniedError``."""
        return self._client._request(
            KeyWithSecretResponse, "POST", "/v1/keys", body=_create_body(name, scopes, principal)
        )


class AsyncKeys(AsyncResource):
    async def list(self) -> KeyListResponse:
        return await self._client._request(KeyListResponse, "GET", "/v1/keys")

    async def get(self, key_id: str) -> KeyResponse:
        return await self._client._request(KeyResponse, "GET", f"/v1/keys/{key_id}")

    async def revoke(self, key_id: str) -> KeyResponse:
        return await self._client._request(KeyResponse, "DELETE", f"/v1/keys/{key_id}")

    async def rotate(self, key_id: str) -> KeyWithSecretResponse:
        return await self._client._request(KeyWithSecretResponse, "POST", f"/v1/keys/{key_id}/rotate")

    async def create(
        self, *, name: str, scopes: Sequence[str], principal: Optional[Any] = None
    ) -> KeyWithSecretResponse:
        return await self._client._request(
            KeyWithSecretResponse, "POST", "/v1/keys", body=_create_body(name, scopes, principal)
        )
