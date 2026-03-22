# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

import pytest

from ros2_medkit_client.client import MedkitClient, normalize_base_url
from ros2_medkit_client.errors import MedkitError


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


class TestMedkitClientProperties:
    async def test_http_before_enter_raises(self):
        client = MedkitClient(base_url="localhost:8080")
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = client.http

    async def test_streams_before_enter_raises(self):
        client = MedkitClient(base_url="localhost:8080")
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = client.streams

    async def test_auth_token_in_stream_headers(self):
        async with MedkitClient(base_url="localhost:8080", auth_token="mytoken") as client:
            assert client.streams._headers.get("Authorization") == "Bearer mytoken"


class TestMedkitClientCall:
    async def test_call_returns_success_result(self):
        """call() returns the result when API function succeeds."""

        async def mock_api_func(*, client, **kwargs):
            return {"items": []}

        async with MedkitClient(base_url="localhost:8080") as client:
            result = await client.call(mock_api_func)
            assert result == {"items": []}

    async def test_call_raises_on_none(self):
        """call() raises MedkitError when API returns None."""

        async def mock_api_func(*, client, **kwargs):
            return None

        async with MedkitClient(base_url="localhost:8080") as client:
            with pytest.raises(MedkitError) as exc_info:
                await client.call(mock_api_func)
            assert exc_info.value.code == "unexpected-status"

    async def test_call_raises_on_generic_error(self):
        """call() raises MedkitError when API returns a GenericError-like object."""

        class FakeGenericError:
            error_code = "entity-not-found"
            message = "Entity x not found"
            parameters = None

        async def mock_api_func(*, client, **kwargs):
            return FakeGenericError()

        async with MedkitClient(base_url="localhost:8080") as client:
            with pytest.raises(MedkitError) as exc_info:
                await client.call(mock_api_func)
            assert exc_info.value.code == "entity-not-found"
            assert exc_info.value.message == "Entity x not found"

    async def test_call_raises_on_generic_error_with_parameters(self):
        """call() preserves error parameters as details."""

        class FakeGenericError:
            error_code = "invalid-parameter"
            message = "Bad value"
            parameters = {"field": "timeout", "reason": "must be positive"}

        async def mock_api_func(*, client, **kwargs):
            return FakeGenericError()

        async with MedkitClient(base_url="localhost:8080") as client:
            with pytest.raises(MedkitError) as exc_info:
                await client.call(mock_api_func)
            assert exc_info.value.details == {"field": "timeout", "reason": "must be positive"}

    async def test_call_converts_unset_parameters_to_none(self):
        """call() converts non-dict parameters (e.g. Unset sentinel) to None."""

        class UnsetType:
            pass

        class FakeGenericError:
            error_code = "some-error"
            message = "Something failed"
            parameters = UnsetType()

        async def mock_api_func(*, client, **kwargs):
            return FakeGenericError()

        async with MedkitClient(base_url="localhost:8080") as client:
            with pytest.raises(MedkitError) as exc_info:
                await client.call(mock_api_func)
            assert exc_info.value.details is None

    async def test_call_passes_kwargs(self):
        """call() forwards kwargs to the API function."""
        received_kwargs = {}

        async def mock_api_func(*, client, **kwargs):
            received_kwargs.update(kwargs)
            return {"items": []}

        async with MedkitClient(base_url="localhost:8080") as client:
            await client.call(mock_api_func, app_id="my_node")
            assert received_kwargs == {"app_id": "my_node"}
