# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

import pytest

from ros2_medkit_client.client import MedkitClient, normalize_base_url


class TestNormalizeBaseUrl:
    def test_adds_http_when_no_protocol(self):
        assert normalize_base_url("localhost:8080") == "http://localhost:8080/api/v1"

    def test_adds_api_v1_when_missing(self):
        assert normalize_base_url("http://localhost:8080") == "http://localhost:8080/api/v1"

    def test_preserves_existing_api_v1(self):
        assert normalize_base_url("http://localhost:8080/api/v1") == "http://localhost:8080/api/v1"

    def test_preserves_https(self):
        assert normalize_base_url("https://gw.example.com") == "https://gw.example.com/api/v1"

    def test_handles_trailing_slash(self):
        assert normalize_base_url("http://localhost:8080/") == "http://localhost:8080/api/v1"

    def test_handles_api_v1_trailing_slash(self):
        assert normalize_base_url("http://localhost:8080/api/v1/") == "http://localhost:8080/api/v1"

    def test_handles_ip_with_port(self):
        assert normalize_base_url("192.168.1.10:8080") == "http://192.168.1.10:8080/api/v1"

    def test_throws_on_empty_string(self):
        with pytest.raises(ValueError, match="base_url is required"):
            normalize_base_url("")

    def test_throws_on_whitespace(self):
        with pytest.raises(ValueError, match="base_url is required"):
            normalize_base_url("   ")


class TestMedkitClient:
    async def test_creates_with_normalized_url(self):
        async with MedkitClient(base_url="localhost:8080") as client:
            assert client.base_url == "http://localhost:8080/api/v1"

    async def test_has_streams(self):
        async with MedkitClient(base_url="localhost:8080") as client:
            assert client.streams is not None
            assert hasattr(client.streams, "faults")
            assert hasattr(client.streams, "trigger_events")
            assert hasattr(client.streams, "subscription_events")

    async def test_context_manager_enters_and_exits(self):
        client = MedkitClient(base_url="localhost:8080")
        async with client:
            pass  # Should not raise
