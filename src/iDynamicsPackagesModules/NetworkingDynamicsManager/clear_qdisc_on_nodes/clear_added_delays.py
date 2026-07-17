"""Import-safe placeholder for legacy delay cleanup."""

from iDynamicsPackagesModules._unsupported import raise_external_configuration_required


def main() -> None:
    """Reject implicit cleanup without caller-provided node configuration."""

    raise_external_configuration_required("delay cleanup")


__all__ = ["main"]

