# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""SSE stream helpers - stub, replaced in Task 5."""

from __future__ import annotations


class StreamHelpers:
    """Placeholder for SSE stream helpers."""

    def __init__(self, *, base_url: str, headers: dict[str, str]) -> None:
        self._base_url = base_url
        self._headers = headers

    def faults(self):
        raise NotImplementedError

    def trigger_events(self, entity_type: str, entity_id: str, trigger_id: str):
        raise NotImplementedError

    def subscription_events(self, entity_type: str, entity_id: str, subscription_id: str):
        raise NotImplementedError
