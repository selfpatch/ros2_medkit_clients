# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

"""Structured error types for the ros2_medkit gateway client."""

from __future__ import annotations


class MedkitError(Exception):
    """Structured error from the ros2_medkit gateway.

    Maps to the gateway's GenericError schema (error_code, message, parameters).
    Provides both normalized names (code, details) and original GenericError
    names (error_code, parameters) for compatibility.
    """

    def __init__(
        self,
        *,
        status: int,
        code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details

    @property
    def error_code(self) -> str:
        """Alias for code - matches GenericError.error_code field name."""
        return self.code

    @property
    def parameters(self) -> dict | None:
        """Alias for details - matches GenericError.parameters field name."""
        return self.details

    @classmethod
    def from_generic_error(
        cls, status: int, error_code: str, message: str, parameters: dict | None = None
    ) -> MedkitError:
        """Create from GenericError schema fields."""
        return cls(status=status, code=error_code, message=message, details=parameters)

    def __repr__(self) -> str:
        return f"MedkitError(status={self.status}, code={self.code!r}, message={self.message!r})"


class MedkitConnectionError(MedkitError):
    """Raised when a connection to the gateway fails."""


class MedkitTimeoutError(MedkitError):
    """Raised when a request to the gateway times out."""
