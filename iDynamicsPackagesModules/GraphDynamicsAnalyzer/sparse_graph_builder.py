"""UPDATED:  Algorithm 1 LSparse call-graph construction utilities for iDynamics.

The previous dense graph builder scans every ordered service pair and queries
Prometheus twice per pair. This module keeps the public output shape, but builds
the graph from active telemetry edges so control-plane work scales with observed
edges instead of all possible pairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Mapping

try:
    import networkx as nx
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    nx = None


class SimpleDiGraph:
    """Small NetworkX-compatible fallback used by non-visual profilers."""

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.edges: dict[tuple[str, str], dict] = {}

    def add_node(self, node: str) -> None:
        self.nodes.add(node)

    def add_edge(self, source: str, destination: str, **attrs) -> None:
        self.nodes.add(source)
        self.nodes.add(destination)
        self.edges[(source, destination)] = attrs

    def number_of_edges(self) -> int:
        return len(self.edges)


@dataclass(frozen=True)
class TrafficEdge:
    source: str
    destination: str
    sent_bytes: float = 0.0
    received_bytes: float = 0.0

    @property
    def stress_bytes(self) -> float:
        return (self.sent_bytes + self.received_bytes) / 2.0


def build_graph_from_traffic_edges(
    services: Iterable[str],
    traffic_edges: Iterable[TrafficEdge],
    min_stress_bytes: float = 0.0,
) -> object:
    """Build a directed weighted graph from already sparse telemetry edges."""
    graph = nx.DiGraph() if nx is not None else SimpleDiGraph()
    service_set = set(services)

    for service in sorted(service_set):
        graph.add_node(service)

    for edge in traffic_edges:
        if edge.source == edge.destination:
            continue
        if edge.source not in service_set or edge.destination not in service_set:
            continue
        if edge.stress_bytes <= min_stress_bytes:
            continue
        graph.add_edge(
            edge.source,
            edge.destination,
            weight=edge.stress_bytes / 1000.0,
            sent_bytes=edge.sent_bytes,
            received_bytes=edge.received_bytes,
            stress_bytes=edge.stress_bytes,
        )

    return graph


def traffic_edges_from_prometheus_series(
    sent_series: Iterable[Mapping],
    received_series: Iterable[Mapping],
    source_label: str = "source_workload",
    destination_label: str = "destination_workload",
) -> list[TrafficEdge]:
    """Merge sent/received Prometheus aggregate series into sparse edges."""
    merged: dict[tuple[str, str], dict[str, float]] = {}

    def add_series(series: Iterable[Mapping], field: str) -> None:
        for item in series:
            metric = item.get("metric", {})
            source = metric.get(source_label)
            destination = metric.get(destination_label)
            if not source or not destination:
                continue
            value = item.get("value", [None, 0])[-1]
            try:
                amount = float(value)
            except (TypeError, ValueError):
                amount = 0.0
            merged.setdefault((source, destination), {"sent_bytes": 0.0, "received_bytes": 0.0})[field] += amount

    add_series(sent_series, "sent_bytes")
    add_series(received_series, "received_bytes")

    return [
        TrafficEdge(source=source, destination=destination, **values)
        for (source, destination), values in sorted(merged.items())
    ]


def build_sparse_prometheus_queries(namespace: str, window: str = "10m") -> tuple[str, str]:
    """Return aggregate PromQL queries for sparse GDA edge discovery."""
    selector = (
        f'reporter="source",'
        f'source_workload!="unknown",'
        f'destination_workload!="unknown",'
        f'source_workload_namespace="{namespace}",'
        f'destination_workload_namespace="{namespace}"'
    )
    sent = (
        "sum by (source_workload, destination_workload) "
        f"(increase(istio_tcp_sent_bytes_total{{{selector}}}[{window}]))"
    )
    received = (
        "sum by (source_workload, destination_workload) "
        f"(increase(istio_tcp_received_bytes_total{{{selector}}}[{window}]))"
    )
    return sent, received


def build_call_graph_sparse(
    namespace: str,
    services: Iterable[str],
    prometheus,
    window: str = "10m",
    min_stress_bytes: float = 0.0,
) -> object:
    """Build a call graph with two aggregate Prometheus queries.

    `prometheus` is intentionally duck typed; it may be a
    prometheus_api_client.PrometheusConnect instance or a test adapter exposing
    `custom_query(query=...)`.
    """
    query_sent, query_received = build_sparse_prometheus_queries(namespace, window=window)
    sent_series = prometheus.custom_query(query=query_sent)
    received_series = prometheus.custom_query(query=query_received)
    traffic_edges = traffic_edges_from_prometheus_series(sent_series, received_series)
    return build_graph_from_traffic_edges(services, traffic_edges, min_stress_bytes=min_stress_bytes)


def legacy_dense_query_count(service_count: int) -> int:
    """Number of Prometheus queries issued by the legacy pairwise builder."""
    return 2 * service_count * (service_count - 1)


def sparse_query_count() -> int:
    """Number of Prometheus queries issued by sparse aggregate edge discovery."""
    return 2


def legacy_time_window(minutes: int) -> tuple[datetime, datetime]:
    end_time = datetime.now()
    return end_time - timedelta(minutes=minutes), end_time
