"""Import-safe placeholder for legacy cluster utility paths."""

from iDynamicsPackagesModules._unsupported import raise_external_configuration_required


def require_explicit_cluster_configuration(operation: str = "cluster utility") -> None:
    """Reject implicit live-cluster execution without explicit configuration."""

    raise_external_configuration_required(operation)


__all__ = ["require_explicit_cluster_configuration"]

