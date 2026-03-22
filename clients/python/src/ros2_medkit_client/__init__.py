# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""Async Python client for the ros2_medkit gateway.

Usage::

    from ros2_medkit_client import MedkitClient, MedkitError
    from ros2_medkit_client.api.discovery import list_apps

    async with MedkitClient(base_url="localhost:8080") as client:
        result = await list_apps.asyncio(client=client.http)

        async for event in client.streams.faults():
            print(event.data)
"""

from ros2_medkit_client.client import MedkitClient, normalize_base_url
from ros2_medkit_client.errors import MedkitConnectionError, MedkitError, MedkitTimeoutError
from ros2_medkit_client.sse import SseEvent, SseStream

__all__ = [
    "MedkitClient",
    "MedkitError",
    "MedkitConnectionError",
    "MedkitTimeoutError",
    "SseStream",
    "SseEvent",
    "normalize_base_url",
]
