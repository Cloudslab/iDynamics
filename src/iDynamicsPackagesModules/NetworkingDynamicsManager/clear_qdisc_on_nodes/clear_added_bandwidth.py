"""Import-safe placeholder for legacy bandwidth cleanup."""

from iDynamicsPackagesModules._unsupported import raise_external_configuration_required


def main() -> None:
    """Reject implicit cleanup without caller-provided node configuration."""

    raise_external_configuration_required("bandwidth cleanup")


__all__ = ["main"]

