# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0
"""Server API - health, version, root endpoint, and the OpenAPI description."""

from ros2_medkit_client._generated.api.server import (
    get_capability_description,
    get_health,
    get_root,
    get_scoped_capability_description,
    get_version_info,
)

__all__ = [
    "get_capability_description",
    "get_health",
    "get_root",
    "get_scoped_capability_description",
    "get_version_info",
]
