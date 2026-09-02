# Copyright 2026 bburda
# SPDX-License-Identifier: Apache-2.0
"""Every api group must import against the code the spec generates.

The rest of the suite exercises the hand-written client and never touches
`ros2_medkit_client.api`, so a group that names a generated module which the
current spec no longer produces stays invisible: the package installs, the suite
passes, and the failure only appears in a consumer, at import time, with the
whole group gone rather than one endpoint.

Two shapes of that have already shipped. Renamed operation ids leave the
re-export pointing at modules that no longer exist. And a body carrying one
schema under two content types is typed `Schema | Unset = UNSET` while the
emitted import line brings in only the UNSET sentinel, so the module raises
NameError on import - generate.sh repairs that, and this is what proves the
repair ran.
"""

import importlib
import pathlib

import pytest

API_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "ros2_medkit_client" / "api"
GROUPS = sorted(p.stem for p in API_DIR.glob("*.py") if p.stem != "__init__")


def test_api_directory_was_found() -> None:
    # Guards the parametrisation itself: a wrong path yields an empty GROUPS and
    # every test below would be skipped rather than failing.
    assert GROUPS, f"no api group modules found under {API_DIR}"


@pytest.mark.parametrize("group", GROUPS)
def test_group_imports(group: str) -> None:
    module = importlib.import_module(f"ros2_medkit_client.api.{group}")
    exported = getattr(module, "__all__", [])
    assert exported, f"{group} re-exports nothing"
    for name in exported:
        assert hasattr(module, name), f"{group}.{name} is listed in __all__ but not bound"


GENERATED_API = API_DIR.parent / "_generated" / "api"
GENERATED_GROUPS = (
    sorted(p.name for p in GENERATED_API.iterdir() if p.is_dir() and not p.name.startswith("__"))
    if GENERATED_API.is_dir()
    else []
)


def test_generated_api_was_found() -> None:
    assert GENERATED_GROUPS, f"no generated api groups under {GENERATED_API}"


@pytest.mark.parametrize("group", GENERATED_GROUPS)
def test_every_generated_endpoint_is_reachable(group: str) -> None:
    """A generated endpoint nobody re-exports cannot be called through this package.

    New operations arrive as new modules under a generated group, and a re-export
    that is not extended leaves them unreachable while every other check stays
    green: the package builds, the group imports, and the endpoint simply is not
    there. Adding a whole group is noticed because the group file is missing;
    adding an operation to an existing group is not, which is the case this
    covers.
    """
    endpoints = {p.stem for p in (GENERATED_API / group).glob("*.py") if p.stem != "__init__"}
    try:
        module = importlib.import_module(f"ros2_medkit_client.api.{group}")
    except ModuleNotFoundError as exc:
        raise AssertionError(f"generated group {group} has no api/{group}.py re-export") from exc
    missing = sorted(endpoints - set(getattr(module, "__all__", [])))
    assert not missing, f"generated but not re-exported by api/{group}.py: {missing}"
