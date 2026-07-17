"""Import-safe placeholder for the legacy controller entry point."""

from iDynamicsPackagesModules._unsupported import raise_external_configuration_required


def main() -> None:
    """Reject implicit controller execution without explicit configuration."""

    raise_external_configuration_required("main controller")


__all__ = ["main"]

