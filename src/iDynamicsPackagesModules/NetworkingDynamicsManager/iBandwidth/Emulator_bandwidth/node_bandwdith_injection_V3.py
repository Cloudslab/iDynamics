"""Import-safe placeholder for legacy bandwidth injection."""

from iDynamicsPackagesModules._unsupported import raise_external_configuration_required


def main() -> None:
    """Reject implicit live-cluster execution without explicit configuration."""

    raise_external_configuration_required("bandwidth injection")


__all__ = ["main"]

