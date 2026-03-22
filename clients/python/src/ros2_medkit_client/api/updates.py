# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0
"""Updates API - software update management."""

from ros2_medkit_client._generated.api.updates import (
    automate_update,
    delete_update,
    execute_update,
    get_update,
    get_update_status,
    list_updates,
    prepare_update,
    register_update,
)

__all__ = [
    "automate_update",
    "delete_update",
    "execute_update",
    "get_update",
    "get_update_status",
    "list_updates",
    "prepare_update",
    "register_update",
]
