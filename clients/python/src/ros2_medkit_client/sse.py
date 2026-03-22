# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""Server-Sent Events (SSE) stream with httpx streaming and auto-reconnect."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator

import httpx

from ros2_medkit_client.errors import MedkitConnectionError, MedkitError, MedkitTimeoutError


@dataclass
class SseEvent:
    """A single Server-Sent Event."""

    event: str = "message"
    data: object = None
    id: str | None = None


def parse_sse_line(line: str, state: dict) -> None:
    """Parse a single SSE line into the accumulator state dict.

    The state dict has keys: event, data, id, retry.
    Trailing ``\\r`` is stripped for CRLF compatibility.
    """
    # Strip trailing \r for CRLF compat
    if line.endswith("\r"):
        line = line[:-1]

    # Comment line
    if line.startswith(":"):
        return

    # Split on first colon
    if ":" in line:
        field_name, _, value = line.partition(":")
        # SSE spec: if value starts with a space, strip it
        if value.startswith(" "):
            value = value[1:]
    else:
        # Line with no colon - field name is the whole line, value is empty
        field_name = line
        value = ""

    if field_name == "event":
        state["event"] = value
    elif field_name == "data":
        if state["data"]:
            state["data"] += "\n" + value
        else:
            state["data"] = value
    elif field_name == "id":
        state["id"] = value
    elif field_name == "retry":
        try:
            state["retry"] = int(value)
        except ValueError:
            pass  # Non-numeric retry values are ignored per SSE spec
    # Unknown fields are silently ignored


def _parse_error_response(response: httpx.Response) -> MedkitError:
    """Parse an HTTP error response into a MedkitError."""
    try:
        body = json.loads(response.content)
        error_code = body.get("error_code", "unknown")
        message = body.get("message", response.reason_phrase or "HTTP error")
        parameters = body.get("parameters")
    except (json.JSONDecodeError, ValueError, AttributeError):
        error_code = "http-error"
        message = response.reason_phrase or f"HTTP {response.status_code}"
        parameters = None

    return MedkitError(
        status=response.status_code,
        code=error_code,
        message=message,
        details=parameters,
    )


class SseStream:
    """Async iterator over Server-Sent Events with auto-reconnect.

    Uses httpx.AsyncClient.stream() for efficient SSE consumption.
    Implements exponential backoff reconnection with Last-Event-ID,
    server retry delay (clamped), buffer limits, and CRLF handling.
    """

    MAX_BUFFER_SIZE = 1024 * 1024  # 1 MB
    MAX_DATA_SIZE = 256 * 1024  # 256 KB

    def __init__(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._url = url
        self._headers = headers or {}
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._max_delay = max_delay

        self._closed = False
        self._last_event_id: str | None = None
        self._server_retry_delay: float | None = None
        self._events_yielded = False
        self._sleep_event: asyncio.Event | None = None

    def close(self) -> None:
        """Stop the stream. Safe to call from any coroutine."""
        self._closed = True
        if self._sleep_event is not None:
            self._sleep_event.set()

    def __aiter__(self) -> AsyncIterator[SseEvent]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[SseEvent]:
        retries = 0
        while not self._closed:
            try:
                async for event in self._connect_and_stream():
                    yield event
                return  # Clean server close
            except MedkitError:
                raise  # HTTP errors are not retried
            except (
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.CloseError,
                OSError,
                httpx.TimeoutException,
            ) as exc:
                if self._closed:
                    return
                # Reset retries if we received events before disconnection
                if self._events_yielded:
                    retries = 0
                    self._events_yielded = False
                retries += 1
                if retries > self._max_retries:
                    if isinstance(exc, httpx.TimeoutException):
                        raise MedkitTimeoutError(
                            status=0,
                            code="timeout",
                            message=str(exc),
                        ) from exc
                    raise MedkitConnectionError(
                        status=0,
                        code="connection-error",
                        message=str(exc),
                    ) from exc
                # Calculate delay
                if self._server_retry_delay is not None:
                    delay = max(0.1, min(self._server_retry_delay, self._max_delay))
                else:
                    delay = min(self._initial_delay * (2 ** (retries - 1)), self._max_delay)
                await self._cancellable_sleep(delay)

    async def _cancellable_sleep(self, seconds: float) -> None:
        """Sleep that can be interrupted by close()."""
        if self._closed:
            return
        self._sleep_event = asyncio.Event()
        try:
            await asyncio.wait_for(self._sleep_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
        finally:
            self._sleep_event = None

    async def _connect_and_stream(self) -> AsyncIterator[SseEvent]:
        """Open a single SSE connection and yield events until it closes."""
        headers = {"Accept": "text/event-stream", **self._headers}
        if self._last_event_id is not None:
            headers["Last-Event-ID"] = self._last_event_id

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=None, write=10.0, pool=10.0),
        ) as http:
            async with http.stream("GET", self._url, headers=headers) as response:
                if response.status_code >= 400:
                    await response.aread()
                    raise _parse_error_response(response)

                buffer = ""
                state = _new_state()

                async for chunk in response.aiter_text():
                    if self._closed:
                        return

                    buffer += chunk
                    if len(buffer) > self.MAX_BUFFER_SIZE:
                        raise MedkitError(
                            status=0,
                            code="sse-buffer-overflow",
                            message=f"SSE buffer exceeded {self.MAX_BUFFER_SIZE} bytes",
                        )

                    # Split on \n (handles both LF and CRLF since \r is stripped later)
                    raw_lines = buffer.split("\n")
                    buffer = raw_lines.pop()  # Last element is incomplete line

                    for line in raw_lines:
                        # Strip trailing \r for CRLF
                        line = line.rstrip("\r")

                        if line == "":
                            # Dispatch: apply id and retry regardless of data presence
                            if state["id"] is not None:
                                self._last_event_id = state["id"]
                            if state["retry"] is not None:
                                self._server_retry_delay = state["retry"] / 1000.0

                            if state["data"]:
                                # Check data size at dispatch
                                if len(state["data"]) > self.MAX_DATA_SIZE:
                                    raise MedkitError(
                                        status=0,
                                        code="sse-data-overflow",
                                        message=f"SSE data exceeded {self.MAX_DATA_SIZE} bytes",
                                    )
                                # Try JSON parse, fall back to raw string
                                try:
                                    parsed = json.loads(state["data"])
                                except (json.JSONDecodeError, ValueError):
                                    parsed = state["data"]

                                self._events_yielded = True
                                yield SseEvent(
                                    event=state["event"],
                                    data=parsed,
                                    id=state["id"],
                                )

                            state = _new_state()
                        else:
                            parse_sse_line(line, state)
                            # Check data size after each line parse
                            if len(state["data"]) > self.MAX_DATA_SIZE:
                                raise MedkitError(
                                    status=0,
                                    code="sse-data-overflow",
                                    message=f"SSE data exceeded {self.MAX_DATA_SIZE} bytes",
                                )


def _new_state() -> dict:
    """Create a fresh SSE parse state accumulator."""
    return {"event": "message", "data": "", "id": None, "retry": None}
