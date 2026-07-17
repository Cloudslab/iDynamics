"""Helpers for the legacy compatibility namespace."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

LEGACY_PACKAGE = "iDynamicsPackagesModules"


def import_legacy_module(module_name: str) -> ModuleType:
    """Import a module from the legacy package namespace."""
    if not module_name or module_name.startswith("."):
        raise ValueError("module_name must be a non-empty relative module path")
    return import_module(f"{LEGACY_PACKAGE}.{module_name}")


__all__ = ["LEGACY_PACKAGE", "import_legacy_module"]
