# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0
"""Faults API - fault listing, clearing, and streaming."""

from ros2_medkit_client._generated.api.faults import (
    clear_all_app_faults,
    clear_all_area_faults,
    clear_all_component_faults,
    clear_all_faults,
    clear_all_function_faults,
    clear_app_fault,
    clear_area_fault,
    clear_component_fault,
    clear_function_fault,
    get_app_fault,
    get_area_fault,
    get_component_fault,
    get_function_fault,
    list_all_faults,
    list_app_faults,
    list_area_faults,
    list_component_faults,
    list_function_faults,
    stream_faults,
)

__all__ = [
    "clear_all_app_faults",
    "clear_all_area_faults",
    "clear_all_component_faults",
    "clear_all_faults",
    "clear_all_function_faults",
    "clear_app_fault",
    "clear_area_fault",
    "clear_component_fault",
    "clear_function_fault",
    "get_app_fault",
    "get_area_fault",
    "get_component_fault",
    "get_function_fault",
    "list_all_faults",
    "list_app_faults",
    "list_area_faults",
    "list_component_faults",
    "list_function_faults",
    "stream_faults",
]
