# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""Tests for SSE stream parsing and reconnection logic."""

from __future__ import annotations

import httpx
import pytest
import respx

from ros2_medkit_client.errors import MedkitError
from ros2_medkit_client.sse import SseEvent, SseStream, parse_sse_line

# ---------------------------------------------------------------------------
# Helper: async byte stream for simulating chunked SSE delivery
# ---------------------------------------------------------------------------


class _AsyncChunkStream(httpx.AsyncByteStream):
    """Yields pre-defined byte chunks, optionally raising after all chunks."""

    def __init__(self, chunks: list[bytes], *, raise_after: BaseException | None = None) -> None:
        self._chunks = chunks
        self._raise_after = raise_after

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk
        if self._raise_after is not None:
            raise self._raise_after


def _sse_response(
    body: str | bytes | None = None,
    *,
    status: int = 200,
    chunks: list[bytes] | None = None,
    raise_after: BaseException | None = None,
) -> dict:
    """Build kwargs for respx .respond() or .mock(side_effect=...)."""
    headers = {"content-type": "text/event-stream"}
    if chunks is not None:
        return {
            "status_code": status,
            "stream": _AsyncChunkStream(chunks, raise_after=raise_after),
            "headers": headers,
        }
    content = body.encode() if isinstance(body, str) else body
    return {"status_code": status, "content": content, "headers": headers}


# ===========================================================================
# parse_sse_line unit tests
# ===========================================================================


class TestParseSseLine:
    """Unit tests for the parse_sse_line function."""

    def _state(self) -> dict:
        return {"event": "message", "data": "", "id": None, "retry": None}

    def test_event_field(self):
        state = self._state()
        parse_sse_line("event: update", state)
        assert state["event"] == "update"

    def test_data_field(self):
        state = self._state()
        parse_sse_line("data: hello", state)
        assert state["data"] == "hello"

    def test_multiline_data(self):
        state = self._state()
        parse_sse_line("data: line1", state)
        parse_sse_line("data: line2", state)
        assert state["data"] == "line1\nline2"

    def test_id_field(self):
        state = self._state()
        parse_sse_line("id: 42", state)
        assert state["id"] == "42"

    def test_retry_field_numeric(self):
        state = self._state()
        parse_sse_line("retry: 3000", state)
        assert state["retry"] == 3000

    def test_retry_field_non_numeric_ignored(self):
        state = self._state()
        parse_sse_line("retry: abc", state)
        assert state["retry"] is None

    def test_comment_ignored(self):
        state = self._state()
        parse_sse_line(": this is a comment", state)
        assert state == self._state()

    def test_unknown_field_ignored(self):
        state = self._state()
        parse_sse_line("foo: bar", state)
        assert state == self._state()

    def test_crlf_stripping(self):
        """Trailing \\r is stripped (CRLF compatibility)."""
        state = self._state()
        parse_sse_line("data: value\r", state)
        assert state["data"] == "value"

    def test_data_without_space_after_colon(self):
        """'data:value' (no space) should still work per SSE spec."""
        state = self._state()
        parse_sse_line("data:nospace", state)
        assert state["data"] == "nospace"

    def test_data_with_empty_value(self):
        """'data:' with no value appends empty string."""
        state = self._state()
        parse_sse_line("data:", state)
        assert state["data"] == ""

    def test_data_with_colons_in_value(self):
        """Only the first colon splits field from value."""
        state = self._state()
        parse_sse_line("data: key: value: extra", state)
        assert state["data"] == "key: value: extra"


# ===========================================================================
# SseEvent tests
# ===========================================================================


class TestSseEvent:
    def test_defaults(self):
        ev = SseEvent()
        assert ev.event == "message"
        assert ev.data is None
        assert ev.id is None

    def test_custom_values(self):
        ev = SseEvent(event="update", data={"key": "val"}, id="7")
        assert ev.event == "update"
        assert ev.data == {"key": "val"}
        assert ev.id == "7"


# ===========================================================================
# SseStream integration tests
# ===========================================================================


class TestSseStream:
    """Integration tests for the SseStream async iterator."""

    @respx.mock
    async def test_parse_events(self):
        """Basic SSE events are parsed and yielded."""
        body = 'event: update\ndata: {"a": 1}\n\ndata: {"b": 2}\n\n'
        respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse")
        events = [ev async for ev in stream]

        assert len(events) == 2
        assert events[0].event == "update"
        assert events[0].data == {"a": 1}
        assert events[1].event == "message"
        assert events[1].data == {"b": 2}

    @respx.mock
    async def test_non_json_data(self):
        """Non-JSON data is returned as a raw string."""
        body = "data: plain text\n\n"
        respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse")
        events = [ev async for ev in stream]

        assert len(events) == 1
        assert events[0].data == "plain text"

    @respx.mock
    async def test_4xx_error_not_retried(self):
        """HTTP 4xx errors raise MedkitError immediately (no retry)."""
        respx.get("http://gw/sse").respond(
            404,
            json={"error_code": "entity-not-found", "message": "Not found"},
        )

        stream = SseStream("http://gw/sse", max_retries=3)
        with pytest.raises(MedkitError) as exc_info:
            async for _ in stream:
                pass

        assert exc_info.value.status == 404
        assert exc_info.value.code == "entity-not-found"

    @respx.mock
    async def test_reconnect_on_network_error(self):
        """Network errors trigger reconnect with Last-Event-ID."""
        # First attempt: one event, then connection drops
        chunks_1 = [b"id: 5\ndata: first\n\n"]
        route = respx.get("http://gw/sse")
        route.side_effect = [
            httpx.Response(
                200,
                stream=_AsyncChunkStream(chunks_1, raise_after=httpx.ReadError("connection reset")),
                headers={"content-type": "text/event-stream"},
            ),
            httpx.Response(
                200,
                content=b"data: second\n\n",
                headers={"content-type": "text/event-stream"},
            ),
        ]

        stream = SseStream("http://gw/sse", max_retries=3, initial_delay=0.01, max_delay=0.01)
        events = [ev async for ev in stream]

        assert len(events) == 2
        assert events[0].data == "first"
        assert events[0].id == "5"
        assert events[1].data == "second"

        # Verify Last-Event-ID was sent on reconnect
        second_request = route.calls[1].request
        assert second_request.headers.get("last-event-id") == "5"

    @respx.mock
    async def test_auth_failure_during_reconnect_no_retry(self):
        """If reconnect gets a 401, MedkitError is raised (no further retries)."""
        route = respx.get("http://gw/sse")
        route.side_effect = [
            httpx.Response(
                200,
                stream=_AsyncChunkStream(
                    [b"data: ok\n\n"],
                    raise_after=httpx.ReadError("connection reset"),
                ),
                headers={"content-type": "text/event-stream"},
            ),
            httpx.Response(
                401,
                json={"error_code": "unauthorized", "message": "Token expired"},
            ),
        ]

        stream = SseStream("http://gw/sse", max_retries=5, initial_delay=0.01, max_delay=0.01)
        with pytest.raises(MedkitError) as exc_info:
            async for _ in stream:
                pass

        assert exc_info.value.status == 401

    @respx.mock
    async def test_max_retries_exhaustion(self):
        """After max_retries, the underlying exception propagates."""
        route = respx.get("http://gw/sse")
        # All attempts fail with network error
        route.side_effect = httpx.ConnectError("refused")

        stream = SseStream("http://gw/sse", max_retries=2, initial_delay=0.01, max_delay=0.01)
        with pytest.raises(httpx.ConnectError):
            async for _ in stream:
                pass

    @respx.mock
    async def test_buffer_overflow(self):
        """Exceeding MAX_BUFFER_SIZE raises MedkitError."""
        huge_chunk = b"x" * (SseStream.MAX_BUFFER_SIZE + 1)
        respx.get("http://gw/sse").respond(**_sse_response(chunks=[huge_chunk]))

        stream = SseStream("http://gw/sse")
        with pytest.raises(MedkitError) as exc_info:
            async for _ in stream:
                pass

        assert exc_info.value.code == "sse-buffer-overflow"

    @respx.mock
    async def test_data_overflow(self):
        """Exceeding MAX_DATA_SIZE raises MedkitError after parse_sse_line."""
        # Build data lines that exceed 256KB total
        big_line = "x" * (SseStream.MAX_DATA_SIZE + 1)
        body = f"data: {big_line}\n\n"
        respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse")
        with pytest.raises(MedkitError) as exc_info:
            async for _ in stream:
                pass

        assert exc_info.value.code == "sse-data-overflow"

    @respx.mock
    async def test_data_overflow_multiline(self):
        """Data overflow detected across multiple data: lines (after each parse)."""
        # Each line is under limit, but combined exceeds it
        half = "y" * (SseStream.MAX_DATA_SIZE // 2 + 1)
        body = f"data: {half}\ndata: {half}\n\n"
        respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse")
        with pytest.raises(MedkitError) as exc_info:
            async for _ in stream:
                pass

        assert exc_info.value.code == "sse-data-overflow"

    @respx.mock
    async def test_close_stops_iteration(self):
        """Calling close() terminates the stream."""
        # Use a stream that would go on forever
        body = b"data: event1\n\n"
        respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse")
        events = []
        async for ev in stream:
            events.append(ev)
            stream.close()

        assert len(events) == 1

    @respx.mock
    async def test_chunked_data(self):
        """SSE data split across multiple chunks is reassembled correctly."""
        chunks = [
            b"data: {\"k",
            b'ey": "val"}\n',
            b"\n",
        ]
        respx.get("http://gw/sse").respond(**_sse_response(chunks=chunks))

        stream = SseStream("http://gw/sse")
        events = [ev async for ev in stream]

        assert len(events) == 1
        assert events[0].data == {"key": "val"}

    @respx.mock
    async def test_id_and_retry_applied_without_data(self):
        """retry and id fields are applied on dispatch even if no data is present."""
        body = "id: 99\nretry: 5000\n\ndata: next\n\n"
        respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse")
        events = [ev async for ev in stream]

        # The first blank line has id/retry but no data - no event yielded but state is applied
        assert len(events) == 1
        assert events[0].data == "next"
        # The last_event_id should have been set by the first dispatch
        assert stream._last_event_id == "99"
        # Server retry delay applied (5000ms = 5.0s)
        assert stream._server_retry_delay == 5.0

    @respx.mock
    async def test_crlf_line_endings(self):
        """CRLF line endings are handled correctly."""
        body = b"data: hello\r\n\r\n"
        respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse")
        events = [ev async for ev in stream]

        assert len(events) == 1
        assert events[0].data == "hello"

    @respx.mock
    async def test_custom_headers_forwarded(self):
        """Custom headers (e.g., auth) are forwarded to the request."""
        body = b"data: ok\n\n"
        route = respx.get("http://gw/sse").respond(**_sse_response(body))

        stream = SseStream("http://gw/sse", headers={"Authorization": "Bearer tok123"})
        events = [ev async for ev in stream]

        assert len(events) == 1
        req = route.calls[0].request
        assert req.headers["authorization"] == "Bearer tok123"
        assert req.headers["accept"] == "text/event-stream"

    @respx.mock
    async def test_retry_counter_reset_after_successful_events(self):
        """Retry counter resets when events were received before disconnect."""
        route = respx.get("http://gw/sse")
        # Attempt 1: yields an event then drops
        # Attempt 2: yields an event then drops (retries reset because events received)
        # Attempt 3: yields an event then drops
        # Attempt 4: clean close
        route.side_effect = [
            httpx.Response(
                200,
                stream=_AsyncChunkStream(
                    [b"data: e1\n\n"], raise_after=httpx.ReadError("drop")
                ),
                headers={"content-type": "text/event-stream"},
            ),
            httpx.Response(
                200,
                stream=_AsyncChunkStream(
                    [b"data: e2\n\n"], raise_after=httpx.ReadError("drop")
                ),
                headers={"content-type": "text/event-stream"},
            ),
            httpx.Response(
                200,
                stream=_AsyncChunkStream(
                    [b"data: e3\n\n"], raise_after=httpx.ReadError("drop")
                ),
                headers={"content-type": "text/event-stream"},
            ),
            httpx.Response(
                200,
                content=b"data: e4\n\n",
                headers={"content-type": "text/event-stream"},
            ),
        ]

        # max_retries=1 would normally fail on 2nd drop, but reset keeps it going
        stream = SseStream("http://gw/sse", max_retries=1, initial_delay=0.01, max_delay=0.01)
        events = [ev async for ev in stream]

        assert [ev.data for ev in events] == ["e1", "e2", "e3", "e4"]

    @respx.mock
    async def test_server_retry_delay_clamped(self):
        """Server retry delay is clamped to [100ms, max_delay]."""
        # Server says retry: 10 (10ms) - should be clamped to 100ms minimum
        body = "retry: 10\ndata: first\n\n"
        route = respx.get("http://gw/sse")
        route.side_effect = [
            httpx.Response(
                200,
                stream=_AsyncChunkStream(
                    [body.encode()], raise_after=httpx.ReadError("drop")
                ),
                headers={"content-type": "text/event-stream"},
            ),
            httpx.Response(
                200,
                content=b"data: second\n\n",
                headers={"content-type": "text/event-stream"},
            ),
        ]

        stream = SseStream("http://gw/sse", max_retries=3, initial_delay=0.5, max_delay=2.0)
        events = [ev async for ev in stream]

        assert len(events) == 2
        # Server retry was 10ms, should be clamped to 0.1s (100ms)
        assert stream._server_retry_delay == 0.01  # 10ms / 1000

    @respx.mock
    async def test_5xx_error_response_body_parsed(self):
        """HTTP 5xx with GenericError JSON body is parsed into MedkitError."""
        respx.get("http://gw/sse").respond(
            500,
            json={"error_code": "internal-error", "message": "Server crashed"},
        )

        stream = SseStream("http://gw/sse", max_retries=0)
        with pytest.raises(MedkitError) as exc_info:
            async for _ in stream:
                pass

        assert exc_info.value.status == 500
        assert exc_info.value.code == "internal-error"
