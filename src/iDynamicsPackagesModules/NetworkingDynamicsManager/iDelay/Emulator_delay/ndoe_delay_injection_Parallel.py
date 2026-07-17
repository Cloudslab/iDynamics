"""Import-safe placeholder for legacy parallel delay injection."""

from iDynamicsPackagesModules._unsupported import raise_external_configuration_required


def main() -> None:
    """Reject implicit live-cluster execution without explicit configuration."""

    raise_external_configuration_required("parallel delay injection")


__all__ = ["main"]

