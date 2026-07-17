"""Import-safe legacy graph-builder facade.

The original module opened cluster clients and embedded deployment-specific
addresses. This compatibility facade keeps the import path available while
requiring callers to pass an already configured telemetry client.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .sparse_graph_builder import build_call_graph_sparse


def build_call_graph(
    namespace: str,
    services: Iterable[str],
    prometheus: Any,
    *,
    window: str = "10m",
    min_stress_bytes: float = 0.0,
) -> object:
    """Build a call graph from aggregate telemetry using caller-supplied clients."""

    if not namespace:
        raise ValueError("namespace must be non-empty")
    if prometheus is None:
        raise ValueError("prometheus client must be provided")
    return build_call_graph_sparse(
        namespace,
        services,
        prometheus,
        window=window,
        min_stress_bytes=min_stress_bytes,
    )


__all__ = ["build_call_graph", "build_call_graph_sparse"]

