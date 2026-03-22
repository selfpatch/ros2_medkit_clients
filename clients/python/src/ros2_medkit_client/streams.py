# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""High-level SSE stream helpers for ros2_medkit gateway endpoints."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from ros2_medkit_client.sse import SseStream

EntityType = Literal["apps", "areas", "components", "functions"]
SubscriptionEntityType = Literal["apps", "components", "functions"]


class StreamHelpers:
    """SSE stream helpers bound to a gateway base URL.

    3 methods cover 8 SSE endpoints:
    - faults() -> GET /faults/stream
    - trigger_events() -> GET /{entity_type}/{id}/triggers/{trigger_id}/events
    - subscription_events() -> GET /{entity_type}/{id}/cyclic-subscriptions/{sub_id}/events
    """

    def __init__(
        self,
        *,
        base_url: str,
        headers: dict[str, str],
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._base_url = base_url
        self._headers = headers
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._max_delay = max_delay

    def _make_stream(self, path: str) -> SseStream:
        return SseStream(
            f"{self._base_url}{path}",
            headers=self._headers,
            max_retries=self._max_retries,
            initial_delay=self._initial_delay,
            max_delay=self._max_delay,
        )

    def faults(self) -> SseStream:
        """Stream real-time fault events from GET /faults/stream."""
        return self._make_stream("/faults/stream")

    def trigger_events(self, entity_type: EntityType, entity_id: str, trigger_id: str) -> SseStream:
        """Stream trigger events. GET /{entity_type}/{entity_id}/triggers/{trigger_id}/events"""
        return self._make_stream(
            f"/{entity_type}/{quote(entity_id, safe='')}/triggers/{quote(trigger_id, safe='')}/events"
        )

    def subscription_events(
        self, entity_type: SubscriptionEntityType, entity_id: str, subscription_id: str
    ) -> SseStream:
        """Stream subscription events. GET /{entity_type}/{entity_id}/cyclic-subscriptions/{sub_id}/events
        Note: areas do not support cyclic subscriptions.
        """
        return self._make_stream(
            f"/{entity_type}/{quote(entity_id, safe='')}"
            f"/cyclic-subscriptions/{quote(subscription_id, safe='')}/events"
        )
