# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""MedkitClient - async context manager for the ros2_medkit gateway."""

from __future__ import annotations

import re
from types import TracebackType
from typing import Any

from ros2_medkit_client.errors import MedkitError
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
        self._entered = False
        self._generated_available = False

    @property
    def base_url(self) -> str:
        """The normalized base URL."""
        return self._base_url

    @property
    def http(self) -> Any:
        """The configured generated Client for use with API functions.

        Returns either Client or AuthenticatedClient from the generated code.
        """
        if self._http is None:
            if self._entered and not self._generated_available:
                raise RuntimeError(
                    "Generated API client not available. Run code generation first "
                    "(./scripts/generate.sh && ln -sf ../../generated src/ros2_medkit_client/_generated). "
                    "SSE streaming via client.streams is still available."
                )
            raise RuntimeError("Client not initialized. Use 'async with MedkitClient(...)' context manager.")
        return self._http

    @property
    def streams(self) -> StreamHelpers:
        """SSE stream helpers for faults, triggers, and subscriptions."""
        if self._streams is None:
            raise RuntimeError("Client not initialized. Use 'async with MedkitClient(...)' context manager.")
        return self._streams

    async def call(self, api_func: Any, **kwargs: Any) -> Any:
        """Call a generated API function, raising MedkitError on errors.

        Bridges the generated code's return-value error handling into exceptions::

            from ros2_medkit_client.api.discovery import list_apps
            apps = await client.call(list_apps.asyncio)

        Args:
            api_func: A generated async API function (e.g., ``list_apps.asyncio``).
            **kwargs: Additional keyword arguments passed to the API function.

        Returns:
            The success response (never GenericError or None).

        Raises:
            MedkitError: If the API returns a GenericError response.
            MedkitError: If the API returns None (unexpected status code).
        """
        result = await api_func(client=self.http, **kwargs)

        if result is None:
            raise MedkitError(
                status=0,
                code="unexpected-status",
                message="API returned an unexpected status code",
            )

        # Check if result is a GenericError (has error_code and message attributes
        # but not items, which would indicate a collection response)
        if hasattr(result, "error_code") and hasattr(result, "message") and not hasattr(result, "items"):
            error_code = getattr(result, "error_code", "unknown")
            message = getattr(result, "message", "Unknown error")
            parameters = getattr(result, "parameters", None)
            # Convert Unset sentinel values to None
            if parameters is not None and not isinstance(parameters, dict):
                parameters = None
            raise MedkitError(
                status=0,
                code=error_code,
                message=message,
                details=parameters if isinstance(parameters, dict) else None,
            )

        return result

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
            self._generated_available = True
        except ImportError:
            # Generated code not available - SSE-only mode
            self._http = None

        self._entered = True

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
