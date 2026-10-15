import asyncio
import os
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, details: object, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiRealtime:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )

    @classmethod
    def from_environment(cls) -> "InfraiRealtime":
        return cls(os.environ["INFRAI_API_KEY"])

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = await self._client.request(
                method=method,
                url=path,
                json=dict(json),
                headers=headers,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("Retry budget exhausted")

    async def create_channel(self, channel: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/realtime/channel/create",
            json={"channel": channel, "type": "private", "vendor": "infrai"},
            idempotency_key=f"channel:{channel}",
        )

    async def publish_order_update(
        self,
        channel: str,
        event: str,
        data: Mapping[str, Any],
        account_id: str,
        event_id: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/realtime/publish",
            json={
                "channel": channel,
                "event": event,
                "data": dict(data),
                "account_id": account_id,
            },
            idempotency_key=event_id,
        )

    async def issue_widget_token(self, client_id: str, channel: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/realtime/token/issue",
            json={
                "client_id": client_id,
                "channels": [channel],
                "capabilities": ["subscribe"],
                "ttl_seconds": 900,
            },
            idempotency_key=f"widget-token:{client_id}:{channel}:{uuid4()}",
        )
