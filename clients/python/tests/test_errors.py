# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0

import pytest

from ros2_medkit_client.errors import MedkitConnectionError, MedkitError, MedkitTimeoutError


class TestMedkitError:
    def test_basic_creation(self):
        err = MedkitError(status=404, code="entity-not-found", message="Entity x not found")
        assert err.status == 404
        assert err.code == "entity-not-found"
        assert err.message == "Entity x not found"
        assert err.details is None
        assert str(err) == "Entity x not found"

    def test_with_details(self):
        err = MedkitError(status=400, code="validation-error", message="Bad input", details={"field": "name"})
        assert err.details == {"field": "name"}

    def test_is_exception(self):
        err = MedkitError(status=500, code="internal", message="fail")
        assert isinstance(err, Exception)
        with pytest.raises(MedkitError):
            raise err

    def test_has_stack_trace(self):
        err = MedkitError(status=500, code="err", message="msg")
        assert isinstance(err, Exception)
        # Python exceptions always have traceback when raised
        try:
            raise err
        except MedkitError as e:
            assert e.__traceback__ is not None

    def test_error_code_alias(self):
        """error_code is alias for code (GenericError compat)."""
        err = MedkitError(status=404, code="entity-not-found", message="not found")
        assert err.error_code == "entity-not-found"

    def test_parameters_alias(self):
        """parameters is alias for details (GenericError compat)."""
        err = MedkitError(status=400, code="err", message="msg", details={"a": 1})
        assert err.parameters == {"a": 1}

    def test_parameters_none_when_no_details(self):
        err = MedkitError(status=400, code="err", message="msg")
        assert err.parameters is None

    def test_from_generic_error(self):
        err = MedkitError.from_generic_error(404, "entity-not-found", "not found", {"key": "val"})
        assert err.status == 404
        assert err.code == "entity-not-found"
        assert err.details == {"key": "val"}

    def test_repr(self):
        err = MedkitError(status=404, code="not-found", message="gone")
        assert "404" in repr(err)
        assert "not-found" in repr(err)


class TestMedkitConnectionError:
    def test_is_medkit_error(self):
        err = MedkitConnectionError(status=0, code="connection-failed", message="DNS error")
        assert isinstance(err, MedkitError)

    def test_catch_broad(self):
        with pytest.raises(MedkitError):
            raise MedkitConnectionError(status=0, code="conn", message="fail")


class TestMedkitTimeoutError:
    def test_is_medkit_error(self):
        err = MedkitTimeoutError(status=0, code="timeout", message="timed out")
        assert isinstance(err, MedkitError)

    def test_catch_narrow(self):
        with pytest.raises(MedkitTimeoutError):
            raise MedkitTimeoutError(status=0, code="timeout", message="timed out")

    def test_catch_broad(self):
        with pytest.raises(MedkitError):
            raise MedkitTimeoutError(status=0, code="timeout", message="timed out")
