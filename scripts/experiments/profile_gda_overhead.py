#!/usr/bin/env python3
"""Synthetic/control-plane overhead profiler for Algorithm 1 graph construction."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from idynamics.gda.sparse import (
    build_graph_from_traffic_edges,
    legacy_dense_query_count,
    sparse_query_count,
)
from idynamics.types import TrafficEdge


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[index]


def generate_edges(service_count: int, edge_factor: int, seed: int) -> list[TrafficEdge]:
    rng = random.Random(seed + service_count * 1009 + edge_factor)
    services = [f"svc-{idx:04d}" for idx in range(service_count)]
    target_edges = min(service_count * edge_factor, service_count * (service_count - 1))
    edges: set[tuple[str, str]] = set()
    while len(edges) < target_edges:
        source = rng.choice(services)
        destination = rng.choice(services)
        if source != destination:
            edges.add((source, destination))
    return [
        TrafficEdge(source=source, destination=destination, sent_bytes_per_s=1000.0, received_bytes_per_s=800.0)
        for source, destination in sorted(edges)
    ]


def time_dense_pair_scan(services: list[str], active_pairs: set[tuple[str, str]]) -> int:
    """Legacy Algorithm 1 control loop: inspect every ordered service pair."""
    found = 0
    for source in services:
        for destination in services:
            if source == destination:
                continue
            if (source, destination) in active_pairs:
                found += 1
    return found


def time_sparse_build(services: list[str], edges: list[TrafficEdge]) -> int:
    graph = build_graph_from_traffic_edges(services, edges)
    return graph.number_of_edges()


def measure_operation(operation) -> tuple[float, float, float, int]:
    """Return wall seconds, process CPU seconds, peak traced MiB, and result."""
    tracemalloc.start()
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    result = operation()
    cpu_seconds = time.process_time() - start_cpu
    wall_seconds = time.perf_counter() - start_wall
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return wall_seconds, cpu_seconds, peak_bytes / (1024.0 * 1024.0), result


def summarize_mode(rows: list[dict[str, object]], mode: str) -> dict[str, object]:
    mode_rows = [row for row in rows if row["mode"] == mode]
    wall_ms = [float(row["graph_build_wall_ms"]) for row in mode_rows]
    cpu_ms = [float(row["graph_build_cpu_ms"]) for row in mode_rows]
    memory_mib = [float(row["peak_python_memory_mib"]) for row in mode_rows]
    query_latency_ms = [float(row["prometheus_query_latency_ms"]) for row in mode_rows]
    return {
        "mode": mode,
        "repetitions": len(mode_rows),
        "graph_build_wall_p50_ms": percentile(wall_ms, 50),
        "graph_build_wall_p95_ms": percentile(wall_ms, 95),
        "graph_build_wall_p99_ms": percentile(wall_ms, 99),
        "graph_build_cpu_p50_ms": percentile(cpu_ms, 50),
        "graph_build_cpu_p95_ms": percentile(cpu_ms, 95),
        "graph_build_cpu_p99_ms": percentile(cpu_ms, 99),
        "peak_python_memory_p50_mib": percentile(memory_mib, 50),
        "peak_python_memory_p95_mib": percentile(memory_mib, 95),
        "peak_python_memory_p99_mib": percentile(memory_mib, 99),
        "prometheus_query_latency_p50_ms": percentile(query_latency_ms, 50),
        "prometheus_query_latency_p95_ms": percentile(query_latency_ms, 95),
        "prometheus_query_latency_p99_ms": percentile(query_latency_ms, 99),
    }


def format_float(value: object) -> object:
    if isinstance(value, float):
        return round(value, 6)
    return value


def dense_enabled(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def time_legacy_pair_scan_for_compatibility(services: list[str], active_pairs: set[tuple[str, str]]) -> tuple[float, int]:
    """Deprecated compatibility helper for older callers."""
    start = time.perf_counter()
    found = time_dense_pair_scan(services, active_pairs)
    return time.perf_counter() - start, found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--sizes", default="50,100,250,500,1000,5000")
    parser.add_argument("--edge-factor", type=int, default=4)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--replicas", type=int, default=1)
    parser.add_argument("--scrape-interval-seconds", type=float, default=15.0)
    parser.add_argument("--prometheus-query-latency-ms", type=float, default=0.0)
    parser.add_argument("--dense-pairwise", action="store_true", help="Enable legacy dense pairwise control-loop comparison.")
    parser.add_argument("--dense-max-services", type=int, default=1000)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    raw_dir = run_dir / "raw"
    processed_dir = run_dir / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    sizes = [int(item) for item in args.sizes.split(",") if item.strip()]
    dense_pairwise = args.dense_pairwise or dense_enabled(os.environ.get("GDA_DENSE_PAIRWISE", "false"))
    summary_rows = []
    raw_rows = []

    for service_count in sizes:
        services = [f"svc-{idx:04d}" for idx in range(service_count)]
        edges = generate_edges(service_count, args.edge_factor, args.seed)
        active_pairs = {(edge.source, edge.destination) for edge in edges}
        service_rows = []
        for repetition in range(args.repetitions):
            sparse_wall, sparse_cpu, sparse_memory, sparse_found = measure_operation(lambda: time_sparse_build(services, edges))
            service_rows.append(
                {
                    "service_count": service_count,
                    "repetition": repetition,
                    "mode": "sparse-aggregate",
                    "scenario": "synthetic_control_plane",
                    "vertex_count": service_count,
                    "active_edges": len(edges),
                    "graph_edges": sparse_found,
                    "replicas": args.replicas,
                    "scrape_interval_seconds": args.scrape_interval_seconds,
                    "query_count": sparse_query_count(),
                    "prometheus_query_latency_ms": sparse_query_count() * args.prometheus_query_latency_ms,
                    "graph_build_wall_ms": sparse_wall * 1000.0,
                    "graph_build_cpu_ms": sparse_cpu * 1000.0,
                    "peak_python_memory_mib": sparse_memory,
                    "dense_pairwise_enabled": dense_pairwise,
                    "dense_skipped_reason": "",
                }
            )
            if dense_pairwise and service_count <= args.dense_max_services:
                dense_wall, dense_cpu, dense_memory, dense_found = measure_operation(lambda: time_dense_pair_scan(services, active_pairs))
                service_rows.append(
                    {
                        "service_count": service_count,
                        "repetition": repetition,
                        "mode": "dense-pairwise",
                        "scenario": "synthetic_control_plane",
                        "vertex_count": service_count,
                        "active_edges": len(edges),
                        "graph_edges": dense_found,
                        "replicas": args.replicas,
                        "scrape_interval_seconds": args.scrape_interval_seconds,
                        "query_count": legacy_dense_query_count(service_count),
                        "prometheus_query_latency_ms": legacy_dense_query_count(service_count) * args.prometheus_query_latency_ms,
                        "graph_build_wall_ms": dense_wall * 1000.0,
                        "graph_build_cpu_ms": dense_cpu * 1000.0,
                        "peak_python_memory_mib": dense_memory,
                        "dense_pairwise_enabled": dense_pairwise,
                        "dense_skipped_reason": "",
                    }
                )
        raw_rows.extend(service_rows)
        for mode in sorted({row["mode"] for row in service_rows}):
            mode_summary = summarize_mode(service_rows, mode)
            query_count = sparse_query_count() if mode == "sparse-aggregate" else legacy_dense_query_count(service_count)
            mode_summary.update(
                {
                    "service_count": service_count,
                    "scenario": "synthetic_control_plane",
                    "vertex_count": service_count,
                    "active_edges": len(edges),
                    "replicas": args.replicas,
                    "scrape_interval_seconds": args.scrape_interval_seconds,
                    "query_count": query_count,
                    "query_reduction_ratio_vs_dense": legacy_dense_query_count(service_count) / query_count,
                    "dense_pairwise_enabled": dense_pairwise,
                    "dense_comparison_status": "measured" if mode == "dense-pairwise" else ("available" if dense_pairwise and service_count <= args.dense_max_services else "sparse_only"),
                }
            )
            summary_rows.append(mode_summary)
        if dense_pairwise and service_count > args.dense_max_services:
            summary_rows.append(
                {
                    "service_count": service_count,
                    "scenario": "synthetic_control_plane",
                    "mode": "dense-pairwise",
                    "vertex_count": service_count,
                    "active_edges": len(edges),
                    "replicas": args.replicas,
                    "scrape_interval_seconds": args.scrape_interval_seconds,
                    "query_count": legacy_dense_query_count(service_count),
                    "query_reduction_ratio_vs_dense": 1.0,
                    "dense_pairwise_enabled": dense_pairwise,
                    "dense_comparison_status": f"skipped_above_{args.dense_max_services}_services",
                    "repetitions": 0,
                    "graph_build_wall_p50_ms": math.nan,
                    "graph_build_wall_p95_ms": math.nan,
                    "graph_build_wall_p99_ms": math.nan,
                    "graph_build_cpu_p50_ms": math.nan,
                    "graph_build_cpu_p95_ms": math.nan,
                    "graph_build_cpu_p99_ms": math.nan,
                    "peak_python_memory_p50_mib": math.nan,
                    "peak_python_memory_p95_mib": math.nan,
                    "peak_python_memory_p99_mib": math.nan,
                    "prometheus_query_latency_p50_ms": legacy_dense_query_count(service_count) * args.prometheus_query_latency_ms,
                    "prometheus_query_latency_p95_ms": legacy_dense_query_count(service_count) * args.prometheus_query_latency_ms,
                    "prometheus_query_latency_p99_ms": legacy_dense_query_count(service_count) * args.prometheus_query_latency_ms,
                }
            )

    with (raw_dir / "gda_overhead_repetitions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw_rows[0]))
        writer.writeheader()
        writer.writerows({key: format_float(value) for key, value in row.items()} for row in raw_rows)

    with (processed_dir / "gda_overhead_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows({key: format_float(value) for key, value in row.items()} for row in summary_rows)

    (processed_dir / "gda_overhead_summary.json").write_text(json.dumps(summary_rows, indent=2, default=str) + "\n")
  
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
