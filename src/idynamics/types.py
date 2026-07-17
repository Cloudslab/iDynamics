"""Typed data structures shared across iDynamics components."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class NodeInfo:
    """Kubernetes worker-node state used by placement policies."""

    name: str
    cpu_capacity_millicores: float
    memory_capacity_mib: float
    cpu_allocated_millicores: float = 0.0
    memory_allocated_mib: float = 0.0
    labels: Mapping[str, str] = field(default_factory=dict)
    taints: tuple[str, ...] = ()
    ready: bool = True

    @property
    def cpu_free_millicores(self) -> float:
        return max(0.0, self.cpu_capacity_millicores - self.cpu_allocated_millicores)

    @property
    def memory_free_mib(self) -> float:
        return max(0.0, self.memory_capacity_mib - self.memory_allocated_mib)


@dataclass(frozen=True)
class PodInfo:
    """Pod or service replica state needed by schedulers."""

    name: str
    namespace: str
    cpu_request_millicores: float
    memory_request_mib: float
    service: str | None = None
    node_name: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)
    sla_latency_ms: float | None = None


@dataclass(frozen=True)
class TrafficEdge:
    """Directed application traffic edge."""

    source: str
    destination: str
    request_rate: float = 0.0
    sent_bytes_per_s: float = 0.0
    received_bytes_per_s: float = 0.0
    latency_ms: float | None = None

    @property
    def stress_bytes_per_s(self) -> float:
        if self.sent_bytes_per_s or self.received_bytes_per_s:
            return (self.sent_bytes_per_s + self.received_bytes_per_s) / 2.0
        return self.request_rate


@dataclass(frozen=True)
class ServiceGraph:
    """Sparse service graph snapshot."""

    services: tuple[str, ...]
    edges: tuple[TrafficEdge, ...]
    timestamp_s: float | None = None

    def edge_weight(self, source: str, destination: str) -> float:
        for edge in self.edges:
            if edge.source == source and edge.destination == destination:
                return edge.stress_bytes_per_s
        return 0.0

    def weighted_edges(self) -> dict[tuple[str, str], float]:
        return {(edge.source, edge.destination): edge.stress_bytes_per_s for edge in self.edges}


@dataclass(frozen=True)
class NetworkMatrix:
    """Time-indexed directed node-to-node latency and bandwidth matrices."""

    node_names: tuple[str, ...]
    latency_ms: tuple[tuple[float, ...], ...]
    bandwidth_mbps: tuple[tuple[float, ...], ...]
    timestamp_s: float = 0.0

    def __post_init__(self) -> None:
        size = len(self.node_names)
        if len(self.latency_ms) != size or len(self.bandwidth_mbps) != size:
            raise ValueError("network matrices must have one row per node")
        for matrix_name, matrix in (("latency_ms", self.latency_ms), ("bandwidth_mbps", self.bandwidth_mbps)):
            if any(len(row) != size for row in matrix):
                raise ValueError(f"{matrix_name} must be square")

    @classmethod
    def from_lists(
        cls,
        node_names: Sequence[str],
        latency_ms: Sequence[Sequence[float]],
        bandwidth_mbps: Sequence[Sequence[float]],
        timestamp_s: float = 0.0,
    ) -> "NetworkMatrix":
        return cls(
            tuple(node_names),
            tuple(tuple(float(value) for value in row) for row in latency_ms),
            tuple(tuple(float(value) for value in row) for row in bandwidth_mbps),
            float(timestamp_s),
        )


@dataclass(frozen=True)
class SchedulingDecision:
    """A scheduler decision with enough context for audit and replay."""

    pod_name: str
    target_node: str
    policy: str
    score: float
    reason: str = ""
    source_node: str | None = None


@dataclass(frozen=True)
class ExperimentLedger:
    """Canonical metadata for a run ledger under ``experiments/runs``."""

    run_id: str
    root: Path
    config_path: Path
    commands_log: Path
    git_sha_path: Path
    git_status_path: Path
    environment_path: Path
    summary_path: Path
    paper_claims_path: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.root / "processed"

    @property
    def figures_dir(self) -> Path:
        return self.root / "figures"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def env_dir(self) -> Path:
        return self.root / "env"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        return data
