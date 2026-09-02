# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0
"""Fault triggers API - fault-driven triggers on an app.

Separate from the triggers API: a trigger there watches a resource on any entity
type, while these fire on the faults of one app and the gateway exposes them on
apps only.
"""

from ros2_medkit_client._generated.api.fault_triggers import (
    create_fault_trigger,
    delete_fault_trigger,
    list_fault_triggers,
)

__all__ = [
    "create_fault_trigger",
    "delete_fault_trigger",
    "list_fault_triggers",
]
