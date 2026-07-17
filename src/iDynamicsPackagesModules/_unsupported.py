"""Shared helpers for legacy modules that require external cluster setup."""

from __future__ import annotations


class ExternalClusterConfigurationRequired(RuntimeError):
    """Raised when a legacy operation needs caller-provided cluster settings."""


def raise_external_configuration_required(operation: str) -> None:
    """Raise a consistent error for removed implicit cluster defaults."""

    raise ExternalClusterConfigurationRequired(
        f"{operation} requires explicit cluster hosts, secret material, and output paths"
    )


__all__ = ["ExternalClusterConfigurationRequired", "raise_external_configuration_required"]
