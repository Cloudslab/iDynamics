"""Modern scheduling-policy protocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from idynamics.types import NetworkMatrix, NodeInfo, PodInfo, SchedulingDecision, ServiceGraph


class SchedulingPolicy(Protocol):
    """Shared interface for Policy 1-4 implementations and experiment agents."""

    name: str

    def plan(
        self,
        pods: Sequence[PodInfo],
        nodes: Sequence[NodeInfo],
        service_graph: ServiceGraph | None = None,
        network: NetworkMatrix | None = None,
    ) -> list[SchedulingDecision]:
        """Return auditable placement or migration decisions."""
