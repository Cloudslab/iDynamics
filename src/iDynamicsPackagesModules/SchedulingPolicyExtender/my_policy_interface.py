"""Legacy scheduling-policy interface with portable data containers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class NodeInfo:
    """Legacy node resource and network summary."""

    node_name: str
    cpu_capacity: float
    mem_capacity: float
    current_cpu_usage: float
    current_mem_usage: float
    network_latency: Mapping[str, float] = field(default_factory=dict)
    network_bandwidth: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PodInfo:
    """Legacy pod scheduling input."""

    pod_name: str
    cpu_req: float
    mem_req: float
    sla_requirement: float
    deployment_name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SchedulingDecision:
    """Legacy scheduling decision container."""

    podInfo_obj: PodInfo
    nodeIno_obj: NodeInfo


class AbstractSchedulingPolicy(ABC):
    """Abstract interface preserved for legacy policy implementations."""

    @abstractmethod
    def initialize_policy(self, dynamics_config: Mapping[str, Any]) -> None:
        """Initialize the policy from explicit configuration."""

    @abstractmethod
    def trigger_migration(self) -> bool:
        """Return whether the policy should produce new scheduling decisions."""

    @abstractmethod
    def schedule_pod(
        self,
        pod: PodInfo,
        candidate_nodes: Sequence[NodeInfo],
    ) -> SchedulingDecision:
        """Return a scheduling decision for one pod."""

    @abstractmethod
    def schedule_all(
        self,
        pods: Sequence[PodInfo],
        candidate_nodes: Sequence[NodeInfo],
    ) -> list[SchedulingDecision]:
        """Return scheduling decisions for a batch of pods."""

    @abstractmethod
    def on_update_metrics(
        self,
        nodes: Sequence[NodeInfo],
        app_namespace: str,
    ) -> None:
        """Update the policy with fresh node and application metrics."""

    @abstractmethod
    def run(self) -> None:
        """Run the policy loop in an embedding application."""


__all__ = [
    "AbstractSchedulingPolicy",
    "NodeInfo",
    "PodInfo",
    "SchedulingDecision",
]

