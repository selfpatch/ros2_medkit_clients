# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""MedkitClient - async context manager for the ros2_medkit gateway."""

from __future__ import annotations

import re
from types import TracebackType

from ros2_medkit_client.streams import StreamHelpers


def normalize_base_url(url: str) -> str:
    """Normalize a gateway URL: add http:// if missing, append /api/v1 if missing.

    Examples:
        >>> normalize_base_url("localhost:8080")
        'http://localhost:8080/api/v1'
        >>> normalize_base_url("http://gw:8080/api/v1")
        'http://gw:8080/api/v1'

    Raises:
        ValueError: If url is empty or whitespace-only.
    """
    if not url.strip():
        raise ValueError("base_url is required")

    normalized = url

    if not re.match(r"^https?://", normalized):
        normalized = f"http://{normalized}"

    normalized = normalized.rstrip("/")

    if not normalized.endswith("/api/v1"):
        normalized = f"{normalized}/api/v1"

    return normalized


class MedkitClient:
    """Async client for the ros2_medkit gateway.

    Usage::

        async with MedkitClient(base_url="localhost:8080") as client:
            # Use generated API functions with client.http
            from ros2_medkit_client.api.discovery import list_apps
            result = await list_apps.asyncio(client=client.http)

            # Stream faults
            async for event in client.streams.faults():
                print(event)

    The auth_token is set at client creation time and cannot be refreshed
    without creating a new client. For long-lived SSE streams, ensure the
    token has sufficient lifetime.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = normalize_base_url(base_url)
        self._auth_token = auth_token
        self._timeout = timeout
        self._http = None
        self._streams: StreamHelpers | None = None

    @property
    def base_url(self) -> str:
        """The normalized base URL."""
        return self._base_url

    @property
    def http(self):
        """The configured generated Client for use with API functions."""
        if self._http is None:
            raise RuntimeError("Client not initialized. Use 'async with MedkitClient(...)' context manager.")
        return self._http

    @property
    def streams(self) -> StreamHelpers:
        """SSE stream helpers for faults, triggers, and subscriptions."""
        if self._streams is None:
            raise RuntimeError("Client not initialized. Use 'async with MedkitClient(...)' context manager.")
        return self._streams

    async def __aenter__(self) -> MedkitClient:
        headers: dict[str, str] = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        # Try to import and use the generated Client
        try:
            from ros2_medkit_client._generated.client import AuthenticatedClient, Client

            if self._auth_token:
                self._http = AuthenticatedClient(
                    base_url=self._base_url,
                    token=self._auth_token,
                    timeout=self._timeout,
                )
            else:
                self._http = Client(
                    base_url=self._base_url,
                    timeout=self._timeout,
                )
            # Enter the generated client's async context (initializes httpx.AsyncClient)
            await self._http.__aenter__()
        except ImportError:
            # Generated code not available - SSE-only mode
            self._http = None

        self._streams = StreamHelpers(
            base_url=self._base_url,
            headers=headers,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._http is not None and hasattr(self._http, "__aexit__"):
            await self._http.__aexit__(exc_type, exc_val, exc_tb)
