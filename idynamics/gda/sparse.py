"""Sparse GDA compatibility layer.
"""

from collections.abc import Iterable

from idynamics.types import TrafficEdge
from iDynamicsPackagesModules.GraphDynamicsAnalyzer import sparse_graph_builder as _legacy
from iDynamicsPackagesModules.GraphDynamicsAnalyzer.sparse_graph_builder import (
    build_call_graph_sparse,
    build_sparse_prometheus_queries,
    legacy_dense_query_count,
    sparse_query_count,
)


def build_graph_from_traffic_edges(
    services: Iterable[str],
    traffic_edges: Iterable[TrafficEdge],
    min_stress_bytes: float = 0.0,
) -> object:
    legacy_edges = [
        _legacy.TrafficEdge(
            source=edge.source,
            destination=edge.destination,
            sent_bytes=edge.sent_bytes_per_s,
            received_bytes=edge.received_bytes_per_s,
        )
        for edge in traffic_edges
    ]
    return _legacy.build_graph_from_traffic_edges(services, legacy_edges, min_stress_bytes=min_stress_bytes)


def traffic_edges_from_prometheus_series(
    sent_series,
    received_series,
    source_label: str = "source_workload",
    destination_label: str = "destination_workload",
) -> list[TrafficEdge]:
    legacy_edges = _legacy.traffic_edges_from_prometheus_series(
        sent_series,
        received_series,
        source_label=source_label,
        destination_label=destination_label,
    )
    return [
        TrafficEdge(
            source=edge.source,
            destination=edge.destination,
            sent_bytes_per_s=edge.sent_bytes,
            received_bytes_per_s=edge.received_bytes,
        )
        for edge in legacy_edges
    ]


__all__ = [
    "build_call_graph_sparse",
    "build_graph_from_traffic_edges",
    "build_sparse_prometheus_queries",
    "legacy_dense_query_count",
    "sparse_query_count",
    "traffic_edges_from_prometheus_series",
]
