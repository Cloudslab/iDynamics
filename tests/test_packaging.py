from __future__ import annotations

import importlib

import pytest


@pytest.mark.packaging
def test_idynamics_version_is_defined() -> None:
    import idynamics

    assert idynamics.__version__ == "0.1.0"


@pytest.mark.packaging
def test_legacy_namespace_imports_policy_interface() -> None:
    module = importlib.import_module(
        "iDynamicsPackagesModules.SchedulingPolicyExtender.my_policy_interface"
    )

    assert hasattr(module, "AbstractSchedulingPolicy")
    assert hasattr(module, "SchedulingDecision")


@pytest.mark.packaging
def test_explicit_legacy_import_helper() -> None:
    from idynamics.legacy import LEGACY_PACKAGE, import_legacy_module

    module = import_legacy_module("SchedulingPolicyExtender.my_policy_interface")

    assert LEGACY_PACKAGE == "iDynamicsPackagesModules"
    assert module.__name__.endswith("my_policy_interface")
