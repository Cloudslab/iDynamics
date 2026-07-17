"""Compatibility exports for legacy graph-analysis imports."""

from .sparse_graph_builder import (
    TrafficEdge,
    build_call_graph_sparse,
    build_graph_from_traffic_edges,
    build_sparse_prometheus_queries,
    legacy_dense_query_count,
    sparse_query_count,
    traffic_edges_from_prometheus_series,
)

__all__ = [
    "TrafficEdge",
    "build_call_graph_sparse",
    "build_graph_from_traffic_edges",
    "build_sparse_prometheus_queries",
    "legacy_dense_query_count",
    "sparse_query_count",
    "traffic_edges_from_prometheus_series",
]

