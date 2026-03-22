# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""Tests for StreamHelpers SSE stream factory methods."""

from __future__ import annotations

import pytest

from ros2_medkit_client.sse import SseStream
from ros2_medkit_client.streams import StreamHelpers

BASE_URL = "http://localhost:8080/api/v1"
AUTH_HEADERS = {"Authorization": "Bearer tok123"}


def _make_helpers(headers: dict[str, str] | None = None) -> StreamHelpers:
    return StreamHelpers(
        base_url=BASE_URL,
        headers=headers or {},
    )


class TestFaults:
    def test_faults_constructs_correct_url(self):
        helpers = _make_helpers()
        stream = helpers.faults()
        assert isinstance(stream, SseStream)
        assert stream._url == f"{BASE_URL}/faults/stream"

    def test_faults_forwards_auth_headers(self):
        helpers = _make_helpers(headers=AUTH_HEADERS)
        stream = helpers.faults()
        assert stream._headers == AUTH_HEADERS


class TestTriggerEvents:
    @pytest.mark.parametrize("entity_type", ["apps", "areas", "components", "functions"])
    def test_trigger_events_entity_types(self, entity_type: str):
        helpers = _make_helpers()
        stream = helpers.trigger_events(entity_type, "my_entity", "trig_1")
        assert isinstance(stream, SseStream)
        assert stream._url == f"{BASE_URL}/{entity_type}/my_entity/triggers/trig_1/events"

    def test_trigger_events_url_encodes_entity_id(self):
        helpers = _make_helpers()
        stream = helpers.trigger_events("apps", "my entity/id", "trig_1")
        assert stream._url == f"{BASE_URL}/apps/my%20entity%2Fid/triggers/trig_1/events"

    def test_trigger_events_url_encodes_trigger_id(self):
        helpers = _make_helpers()
        stream = helpers.trigger_events("apps", "entity", "trig id/1")
        assert stream._url == f"{BASE_URL}/apps/entity/triggers/trig%20id%2F1/events"

    def test_trigger_events_url_encodes_special_chars(self):
        helpers = _make_helpers()
        stream = helpers.trigger_events("components", "comp#1", "trig?x=1")
        assert stream._url == f"{BASE_URL}/components/comp%231/triggers/trig%3Fx%3D1/events"

    def test_trigger_events_forwards_auth_headers(self):
        helpers = _make_helpers(headers=AUTH_HEADERS)
        stream = helpers.trigger_events("apps", "entity", "trig_1")
        assert stream._headers == AUTH_HEADERS


class TestSubscriptionEvents:
    @pytest.mark.parametrize("entity_type", ["apps", "components", "functions"])
    def test_subscription_events_entity_types(self, entity_type: str):
        helpers = _make_helpers()
        stream = helpers.subscription_events(entity_type, "my_entity", "sub_1")
        assert isinstance(stream, SseStream)
        assert stream._url == f"{BASE_URL}/{entity_type}/my_entity/cyclic-subscriptions/sub_1/events"

    def test_subscription_events_url_encodes_entity_id(self):
        helpers = _make_helpers()
        stream = helpers.subscription_events("apps", "my entity/id", "sub_1")
        assert stream._url == f"{BASE_URL}/apps/my%20entity%2Fid/cyclic-subscriptions/sub_1/events"

    def test_subscription_events_url_encodes_subscription_id(self):
        helpers = _make_helpers()
        stream = helpers.subscription_events("apps", "entity", "sub id/1")
        assert stream._url == f"{BASE_URL}/apps/entity/cyclic-subscriptions/sub%20id%2F1/events"

    def test_subscription_events_url_encodes_special_chars(self):
        helpers = _make_helpers()
        stream = helpers.subscription_events("functions", "func#1", "sub?x=1")
        assert stream._url == f"{BASE_URL}/functions/func%231/cyclic-subscriptions/sub%3Fx%3D1/events"

    def test_subscription_events_forwards_auth_headers(self):
        helpers = _make_helpers(headers=AUTH_HEADERS)
        stream = helpers.subscription_events("apps", "entity", "sub_1")
        assert stream._headers == AUTH_HEADERS


class TestStreamHelperParams:
    def test_default_retry_params_passed_to_stream(self):
        helpers = StreamHelpers(base_url=BASE_URL, headers={})
        stream = helpers.faults()
        assert stream._max_retries == 5
        assert stream._initial_delay == 1.0
        assert stream._max_delay == 30.0

    def test_custom_retry_params_passed_to_stream(self):
        helpers = StreamHelpers(
            base_url=BASE_URL,
            headers={},
            max_retries=10,
            initial_delay=0.5,
            max_delay=60.0,
        )
        stream = helpers.faults()
        assert stream._max_retries == 10
        assert stream._initial_delay == 0.5
        assert stream._max_delay == 60.0

    def test_custom_retry_params_passed_to_trigger_stream(self):
        helpers = StreamHelpers(
            base_url=BASE_URL,
            headers={},
            max_retries=3,
            initial_delay=2.0,
            max_delay=15.0,
        )
        stream = helpers.trigger_events("apps", "entity", "trig_1")
        assert stream._max_retries == 3
        assert stream._initial_delay == 2.0
        assert stream._max_delay == 15.0

    def test_custom_retry_params_passed_to_subscription_stream(self):
        helpers = StreamHelpers(
            base_url=BASE_URL,
            headers={},
            max_retries=7,
            initial_delay=0.1,
            max_delay=20.0,
        )
        stream = helpers.subscription_events("components", "entity", "sub_1")
        assert stream._max_retries == 7
        assert stream._initial_delay == 0.1
        assert stream._max_delay == 20.0
