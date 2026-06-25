"""External benchmark adapter registry."""

from idynamics.workloads.adapters.base import BenchmarkAdapter, EndpointSpec, WorkloadGeneratorSpec
from idynamics.workloads.adapters.registry import ADAPTERS, get_adapter, iter_adapters

__all__ = [
    "ADAPTERS",
    "BenchmarkAdapter",
    "EndpointSpec",
    "WorkloadGeneratorSpec",
    "get_adapter",
    "iter_adapters",
]
