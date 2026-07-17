"""Import-safe placeholder for legacy parallel delay measurement."""

from iDynamicsPackagesModules._unsupported import raise_external_configuration_required


def main() -> None:
    """Reject implicit live-cluster execution without explicit configuration."""

    raise_external_configuration_required("parallel delay measurement")


__all__ = ["main"]

