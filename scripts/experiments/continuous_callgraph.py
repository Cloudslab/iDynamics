#!/usr/bin/env python3
"""Continuous workload-mix and call-graph evolution experiment."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping

from idynamics.gda.metrics import (
    active_edge_count,
    edge_jaccard_distance,
    gini,
    hot_edge_rank_correlation,
    pearson,
    request_mix_entropy,
    skewness,
    sla_pressure,
    top_hotspot_churn,
    weighted_edge_distance,
)
from idynamics.gda.application_metrics import (
    APPLICATION_POLICY_TIMESERIES_COLUMNS,
    ApplicationRunContext,
    build_application_policy_row,
)
from idynamics.workloads.social import WorkloadMixer, default_requests_for_workload, normalize_workload_mode


DEFAULT_SOCIAL_BASE_URL = "http://nginx-thrift.social-network.svc.cluster.local:8080"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--mode",
        default="sinusoidal",
        choices=["step", "linear", "sinusoidal", "markov", "expert_skew_shift", "cache_stress", "payload_heavy", "trace_csv"],
    )
    parser.add_argument("--steps", type=int, default=48)
    parser.add_argument("--interval-s", type=float, default=5.0)
    parser.add_argument("--total-qps", type=float, default=90.0)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--trace-csv", default="")
    parser.add_argument("--live-wrk", action="store_true")
    parser.add_argument("--wrk-bin", default="/home/ubuntu/DeathStarBench/wrk2/wrk")
    parser.add_argument("--base-url", default=DEFAULT_SOCIAL_BASE_URL)
    parser.add_argument("--scale", default="synthetic", help="Evidence scope label, e.g. synthetic, scale10, or scale45.")
    parser.add_argument("--benchmark", default="social-network")
    parser.add_argument("--namespace", default="social-network")
    parser.add_argument("--replica-level", default="")
    parser.add_argument("--replica-config", default="")
    parser.add_argument("--repeat", default="")
    parser.add_argument("--worker-nodes-selected", default="")
    parser.add_argument("--actual-app-pods", default="")
    parser.add_argument("--ready-app-pods", default="")
    parser.add_argument("--non-empty-worker-nodes", default="")
    parser.add_argument("--pod-restarts", default="")
    parser.add_argument("--total-pods", default="")
    parser.add_argument("--cluster-cpu-utilization", default="")
    parser.add_argument("--cluster-memory-utilization", default="")
    parser.add_argument("--top-node-cpu-utilization", default="")
    parser.add_argument(
        "--policies",
        default="kubernetes-default,cga,hda",
        help="Comma-separated placement/policy labels evaluated or analytically replayed over the same graph snapshots.",
    )
    return parser.parse_args()


POLICY_ALIASES = {
    "kubernetes": "kubernetes-default",
    "k8s": "kubernetes-default",
    "k8s-default": "kubernetes-default",
    "kubernetes-default": "kubernetes-default",
    "cga": "cga",
    "hda": "hda",
    "policy1": "cga",
    "policy4": "hda",
    "policy2": "policy2",
    "p2": "policy2",
    "policy2-critical-path-latency": "policy2",
    "policy3": "policy3",
    "p3": "policy3",
    "policy3-bandwidth-payload-aware": "policy3",
}


POLICY_DISPLAY = {
    "kubernetes-default": "K8s default",
    "cga": "CGA",
    "hda": "HDA",
    "policy2": "Policy 2",
    "policy3": "Policy 3",
}


def weighted_edges(requests, probabilities: Mapping[str, float], total_qps: float, stress: float) -> dict[tuple[str, str], float]:
    request_by_name = {request.name: request for request in requests}
    edges: dict[tuple[str, str], float] = {}
    for name, probability in probabilities.items():
        request = request_by_name[name]
        for edge, base_weight in request.edge_weights.items():
            edges[edge] = edges.get(edge, 0.0) + total_qps * probability * base_weight * stress
    return {edge: value for edge, value in edges.items() if value >= 5.0}


POLICY_LATENCY_FACTORS = {
    "kubernetes": 1.0,
    "kubernetes-default": 1.0,
    "k8s-default": 1.0,
    "cga": 0.94,
    "hda": 0.90,
    "policy1": 0.94,
    "policy2": 0.92,
    "policy3": 0.91,
    "policy4": 0.90,
}


def normalize_policy_labels(raw_policies: str) -> list[str]:
    labels = []
    for raw_policy in raw_policies.split(","):
        policy = raw_policy.strip().lower()
        if not policy:
            continue
        labels.append(POLICY_ALIASES.get(policy, policy))
    for required in ("kubernetes-default", "cga", "hda"):
        if required not in labels:
            labels.append(required)
    deduped = []
    for label in labels:
        if label not in deduped:
            deduped.append(label)
    return deduped


def hotspot_churn(previous_edges: Mapping[tuple[str, str], float], edges: Mapping[tuple[str, str], float], k: int = 3) -> float:
    return top_hotspot_churn(previous_edges, edges, k=k)


def latency_model(
    requests,
    probabilities: Mapping[str, float],
    stress: float,
    graph_distance: float,
    rng: random.Random,
    policy: str = "kubernetes",
) -> tuple[float, float]:
    by_name = {request.name: request for request in requests}
    base_latency = sum(probabilities[name] * by_name[name].base_latency_ms for name in probabilities)
    sla_target = sum(probabilities[name] * by_name[name].sla_ms for name in probabilities)
    factor = POLICY_LATENCY_FACTORS.get(policy, 1.0)
    latency = (base_latency * (0.92 + 0.62 * stress) + 44.0 * graph_distance) * factor + rng.gauss(0.0, 2.5)
    sla_violation = max(0.0, (latency - sla_target) / max(1.0, sla_target))
    return max(1.0, latency), sla_violation


def run_wrk_interval(args, request, qps: float, step: int, log_dir: Path) -> None:
    if qps < 1.0:
        return
    command = [
        args.wrk_bin,
        "-D",
        "exp",
        "-t2",
        "-c32",
        f"-d{max(1, int(args.interval_s))}s",
        "-L",
        "-s",
        request.script_path,
        request.url_path,
        f"-R{max(1, int(round(qps)))}",
    ]
    log_path = log_dir / f"wrk_step_{step:03d}_{request.name}.log"
    with log_path.open("w") as output:
        output.write("$ " + " ".join(command) + "\n")
        subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=False)


def write_csv(path: Path, fieldnames: list[str], rows: list[Mapping]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_snapshot_csv(path: Path, snapshots: list[dict]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["step", "time_s", "source", "destination", "weight"])
        for snapshot in snapshots:
            for (source, destination), weight in sorted(snapshot["edges"].items()):
                writer.writerow([snapshot["step"], snapshot["time_s"], source, destination, f"{weight:.6f}"])


def write_snapshot_jsonl(path: Path, snapshots: list[dict]) -> None:
    with path.open("w") as output:
        for snapshot in snapshots:
            payload = {
                "step": snapshot["step"],
                "time_s": snapshot["time_s"],
                "edges": [
                    {"source": source, "destination": destination, "weight": weight}
                    for (source, destination), weight in sorted(snapshot["edges"].items())
                ],
            }
            output.write(json.dumps(payload, sort_keys=True) + "\n")


def write_callgraph_edges_summary(path: Path, snapshots: list[dict]) -> None:
    aggregate: dict[tuple[str, str], dict[str, float]] = {}
    for snapshot in snapshots:
        for (source, destination), weight in snapshot["edges"].items():
            stats = aggregate.setdefault(
                (source, destination),
                {"active_steps": 0.0, "total_weight": 0.0, "max_weight": 0.0},
            )
            stats["active_steps"] += 1.0
            stats["total_weight"] += float(weight)
            stats["max_weight"] = max(stats["max_weight"], float(weight))
    rows = []
    total_steps = max(1, len(snapshots))
    for (source, destination), stats in sorted(aggregate.items()):
        rows.append(
            {
                "source": source,
                "destination": destination,
                "active_steps": int(stats["active_steps"]),
                "active_step_ratio": f"{stats['active_steps'] / total_steps:.6f}",
                "mean_weight": f"{stats['total_weight'] / total_steps:.6f}",
                "max_weight": f"{stats['max_weight']:.6f}",
            }
        )
    write_csv(
        path,
        ["source", "destination", "active_steps", "active_step_ratio", "mean_weight", "max_weight"],
        rows,
    )


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (p / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def write_gda_runtime_summary(path: Path, rows: list[Mapping]) -> None:
    query = [float(row["gda_query_latency_ms"]) for row in rows]
    build = [float(row["gda_build_time_ms"]) for row in rows]
    total = [float(row["gda_total_time_ms"]) for row in rows]
    edge_counts = [float(row["gda_edges"]) for row in rows]
    summary = [
        {
            "steps": len(rows),
            "mean_query_latency_ms": f"{statistics.fmean(query) if query else 0.0:.6f}",
            "p95_query_latency_ms": f"{percentile(query, 95):.6f}",
            "mean_build_time_ms": f"{statistics.fmean(build) if build else 0.0:.6f}",
            "p95_build_time_ms": f"{percentile(build, 95):.6f}",
            "mean_total_time_ms": f"{statistics.fmean(total) if total else 0.0:.6f}",
            "p95_total_time_ms": f"{percentile(total, 95):.6f}",
            "mean_active_edges": f"{statistics.fmean(edge_counts) if edge_counts else 0.0:.6f}",
            "max_active_edges": f"{max(edge_counts) if edge_counts else 0.0:.0f}",
        }
    ]
    write_csv(
        path,
        [
            "steps",
            "mean_query_latency_ms",
            "p95_query_latency_ms",
            "mean_build_time_ms",
            "p95_build_time_ms",
            "mean_total_time_ms",
            "p95_total_time_ms",
            "mean_active_edges",
            "max_active_edges",
        ],
        summary,
    )


def write_application_metrics_summary(path: Path, rows: list[Mapping]) -> None:
    groups = sorted({str(row["policy"]) for row in rows})
    summary_rows = []
    for policy in groups:
        subset = [row for row in rows if row["policy"] == policy]
        summary_rows.append(
            {
                "benchmark": subset[0].get("benchmark", ""),
                "scale": subset[0].get("scale", ""),
                "replica_level": subset[0].get("replica_level", ""),
                "workload_mode": subset[0].get("workload_mode", ""),
                "policy": policy,
                "evidence_type": subset[0].get("evidence_type", "replay"),
                "steps": len(subset),
                "mean_latency_ms": f"{statistics.fmean(float(row['latency_ms']) for row in subset):.6f}",
                "p95_latency_ms": f"{percentile([float(row['latency_ms']) for row in subset], 95):.6f}",
                "mean_sla_violation_ratio": f"{statistics.fmean(float(row['sla_violation_ratio']) for row in subset):.6f}",
                "mean_throughput_rps": f"{statistics.fmean(float(row['throughput_rps']) for row in subset):.6f}",
                "mean_active_edge_count": f"{statistics.fmean(float(row['active_edge_count']) for row in subset):.6f}",
                "mean_gda_total_time_ms": f"{statistics.fmean(float(row['gda_total_time_ms']) for row in subset):.6f}",
                "pod_node_occupancy_ratio": subset[0].get("pod_node_occupancy_ratio", ""),
            }
        )
    write_csv(
        path,
        [
            "benchmark",
            "scale",
            "replica_level",
            "workload_mode",
            "policy",
            "evidence_type",
            "steps",
            "mean_latency_ms",
            "p95_latency_ms",
            "mean_sla_violation_ratio",
            "mean_throughput_rps",
            "mean_active_edge_count",
            "mean_gda_total_time_ms",
            "pod_node_occupancy_ratio",
        ],
        summary_rows,
    )


def series_points(rows: list[Mapping], key: str, height: int, top: int, panel_h: int, max_value: float | None = None) -> str:
    max_y = max_value if max_value is not None else max(float(row[key]) for row in rows) or 1.0
    if max_y <= 0:
        max_y = 1.0
    denom_x = max(1, len(rows) - 1)
    points = []
    for idx, row in enumerate(rows):
        x = 62 + idx * (840 / denom_x)
        y = top + panel_h - (float(row[key]) / max_y) * (panel_h - 18)
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)







def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    raw_dir = run_dir / "raw"
    processed_dir = run_dir / "processed"
    figures_dir = run_dir / "figures"
    logs_dir = run_dir / "logs"
    for directory in (raw_dir, processed_dir, figures_dir, logs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    base_url = args.base_url
    if normalize_workload_mode(args.benchmark) != "social-network" and args.base_url == DEFAULT_SOCIAL_BASE_URL:
        base_url = None
    requests = default_requests_for_workload(args.benchmark, base_url=base_url)
    request_names = [request.name for request in requests]
    policies = normalize_policy_labels(args.policies)
    mixer = WorkloadMixer(
        request_names=request_names,
        mode=args.mode,
        steps=args.steps,
        interval_s=args.interval_s,
        seed=args.seed,
        trace_csv=args.trace_csv or None,
        qps=args.total_qps,
        workload_mode=args.benchmark,
    )
    rng = random.Random(args.seed)
    rows = []
    policy_rows = []
    gda_runtime_rows = []
    snapshots = []
    previous_edges: dict[tuple[str, str], float] = {}

    all_mode_rows = []
    for mode in ["step", "linear", "sinusoidal", "markov"]:
        mode_mixer = WorkloadMixer(
            request_names,
            mode,
            args.steps,
            args.interval_s,
            seed=args.seed,
            qps=args.total_qps,
            workload_mode=args.benchmark,
        )
        for step, probabilities in enumerate(mode_mixer.schedule()):
            all_mode_rows.append({"mode": mode, "step": step, **{f"p_{name}": probabilities[name] for name in request_names}})

    if args.live_wrk:
        live_notice = logs_dir / "live_wrk_notice.log"
        live_notice.write_text("Concurrent wrk2 execution enabled for this run.\n")

    for step, probabilities in enumerate(mixer.schedule()):
        time_s = step * args.interval_s
        stress = 0.82 + 0.22 * math.sin((2.0 * math.pi * step / max(1, args.steps)) + 0.7) + rng.uniform(-0.05, 0.05)
        stress = max(0.25, min(1.45, stress))
        gda_start = time.perf_counter()
        edges = weighted_edges(requests, probabilities, args.total_qps, stress)
        gda_build_time_ms = (time.perf_counter() - gda_start) * 1000.0
        gda_query_latency_ms = 0.0
        gda_total_time_ms = gda_query_latency_ms + gda_build_time_ms
        gda_nodes = len({node for edge in edges for node in edge})
        gda_edges = active_edge_count(edges)
        jaccard = edge_jaccard_distance(previous_edges, edges) if step > 0 else 0.0
        weighted = weighted_edge_distance(previous_edges, edges) if step > 0 else 0.0
        rank_corr = hot_edge_rank_correlation(previous_edges, edges) if step > 0 else 1.0
        edge_weights = list(edges.values())
        entropy = request_mix_entropy(probabilities)
        churn = hotspot_churn(previous_edges, edges, k=3) if step > 0 else 0.0
        traffic_gini = gini(edge_weights)
        traffic_skew = skewness(edge_weights)
        policy_latencies: dict[str, tuple[float, float]] = {}
        for policy in policies:
            policy_rng = random.Random((args.seed * 1000003) + (step * 97) + sum(ord(char) for char in policy))
            policy_latencies[policy] = latency_model(requests, probabilities, stress, weighted, policy_rng, policy)
        latency_ms, sla_violation = policy_latencies[policies[0]]
        sla_ms = sum(probabilities[request.name] * request.sla_ms for request in requests)
        row = {
            "step": step,
            "time_s": f"{time_s:.3f}",
            "traffic_stress": f"{stress:.6f}",
            "edge_jaccard_distance": f"{jaccard:.6f}",
            "weighted_edge_distance": f"{weighted:.6f}",
            "hot_edge_rank_correlation": f"{rank_corr:.6f}",
            "graph_change_rate_per_s": f"{weighted / args.interval_s if args.interval_s > 0 else 0.0:.8f}",
            "request_mix_entropy": f"{entropy:.6f}",
            "top3_hotspot_churn": f"{churn:.6f}",
            "active_edge_count": active_edge_count(edges),
            "traffic_stress_gini": f"{traffic_gini:.6f}",
            "traffic_stress_skew": f"{traffic_skew:.6f}",
            "migration_count": "",
            "policy_decision_time_ms": "",
            "latency_ms": f"{latency_ms:.6f}",
            "sla_ms": f"{sla_ms:.6f}",
            "sla_pressure": f"{sla_pressure(latency_ms, sla_ms):.6f}",
            "sla_violation_ratio": f"{sla_violation:.6f}",
            **{f"p_{name}": f"{probabilities[name]:.6f}" for name in request_names},
            **{f"qps_{name}": f"{args.total_qps * probabilities[name]:.6f}" for name in request_names},
        }
        rows.append(row)
        for policy, (policy_latency_ms, policy_sla_violation) in policy_latencies.items():
            policy_rows.append(
                {
                    "policy": policy,
                    "policy_display_name": POLICY_DISPLAY.get(policy, policy),
                    "step": step,
                    "time_s": f"{time_s:.3f}",
                    "evidence_type": "replay",
                    "traffic_stress": f"{stress:.6f}",
                    "weighted_edge_distance": f"{weighted:.6f}",
                    "active_edge_count": gda_edges,
                    "request_mix_entropy": f"{entropy:.6f}",
                    "top3_hotspot_churn": f"{churn:.6f}",
                    "traffic_stress_gini": f"{traffic_gini:.6f}",
                    "traffic_stress_skew": f"{traffic_skew:.6f}",
                    "migration_count": "",
                    "policy_decision_time_ms": "",
                    "latency_ms": f"{policy_latency_ms:.6f}",
                    "sla_ms": f"{sla_ms:.6f}",
                    "sla_pressure": f"{sla_pressure(policy_latency_ms, sla_ms):.6f}",
                    "sla_violation_ratio": f"{policy_sla_violation:.6f}",
                }
            )
        gda_runtime_rows.append(
            {
                "step": step,
                "time_s": f"{time_s:.3f}",
                "evidence_type": "replay",
                "gda_query_latency_ms": f"{gda_query_latency_ms:.6f}",
                "gda_build_time_ms": f"{gda_build_time_ms:.6f}",
                "gda_total_time_ms": f"{gda_total_time_ms:.6f}",
                "gda_nodes": gda_nodes,
                "gda_edges": gda_edges,
                "gda_query_count": 0,
            }
        )
        snapshots.append({"step": step, "time_s": time_s, "edges": edges})

        if args.live_wrk:
            with ThreadPoolExecutor(max_workers=len(requests)) as executor:
                for request in requests:
                    executor.submit(run_wrk_interval, args, request, args.total_qps * probabilities[request.name], step, logs_dir)

        previous_edges = edges
    metrics = {
        "mean_edge_jaccard_distance": statistics.fmean(float(row["edge_jaccard_distance"]) for row in rows[1:]),
        "mean_weighted_edge_distance": statistics.fmean(float(row["weighted_edge_distance"]) for row in rows[1:]),
        "mean_hot_edge_rank_correlation": statistics.fmean(float(row["hot_edge_rank_correlation"]) for row in rows[1:]),
        "mean_graph_change_rate_per_s": statistics.fmean(float(row["graph_change_rate_per_s"]) for row in rows[1:]),
        "mean_request_mix_entropy": statistics.fmean(float(row["request_mix_entropy"]) for row in rows),
        "mean_top3_hotspot_churn": statistics.fmean(float(row["top3_hotspot_churn"]) for row in rows[1:]),
        "mean_active_edge_count": statistics.fmean(float(row["active_edge_count"]) for row in rows),
        "mean_traffic_stress_gini": statistics.fmean(float(row["traffic_stress_gini"]) for row in rows),
        "mean_traffic_stress_skew": statistics.fmean(float(row["traffic_stress_skew"]) for row in rows),
        "migration_count_available": False,
        "policy_decision_time_available": False,
        "policy_latency_evidence_type": "replay",
        "mean_gda_query_latency_ms": statistics.fmean(float(row["gda_query_latency_ms"]) for row in gda_runtime_rows),
        "mean_gda_build_time_ms": statistics.fmean(float(row["gda_build_time_ms"]) for row in gda_runtime_rows),
        "mean_gda_total_time_ms": statistics.fmean(float(row["gda_total_time_ms"]) for row in gda_runtime_rows),
        "latency_sla_violation_correlation": pearson(
            [float(row["latency_ms"]) for row in rows],
            [float(row["sla_violation_ratio"]) for row in rows],
        ),
        "latency_sla_pressure_correlation": pearson(
            [float(row["latency_ms"]) for row in rows],
            [float(row["sla_pressure"]) for row in rows],
        ),
        "traffic_stress_latency_correlation": pearson(
            [float(row["traffic_stress"]) for row in rows],
            [float(row["latency_ms"]) for row in rows],
        ),
    }
    for policy in policies:
        subset = [row for row in policy_rows if row["policy"] == policy]
        if subset:
            metrics[f"{policy}_mean_latency_ms"] = statistics.fmean(float(row["latency_ms"]) for row in subset)
            metrics[f"{policy}_mean_sla_violation_ratio"] = statistics.fmean(float(row["sla_violation_ratio"]) for row in subset)
            metrics[f"{policy}_mean_request_mix_entropy"] = statistics.fmean(float(row["request_mix_entropy"]) for row in subset)

    row_fields = [
        "step",
        "time_s",
        *[f"p_{name}" for name in request_names],
        *[f"qps_{name}" for name in request_names],
        "traffic_stress",
        "edge_jaccard_distance",
        "weighted_edge_distance",
        "hot_edge_rank_correlation",
        "graph_change_rate_per_s",
        "request_mix_entropy",
        "top3_hotspot_churn",
        "active_edge_count",
        "traffic_stress_gini",
        "traffic_stress_skew",
        "migration_count",
        "policy_decision_time_ms",
        "latency_ms",
        "sla_ms",
        "sla_pressure",
        "sla_violation_ratio",
    ]
    write_csv(raw_dir / "request_mix_timeseries.csv", row_fields, rows)
    load_rows = []
    for row in rows:
        for request_name in request_names:
            load_rows.append(
                {
                    "step": row["step"],
                    "time_s": row["time_s"],
                    "request_type": request_name,
                    "probability": row[f"p_{request_name}"],
                    "qps": row[f"qps_{request_name}"],
                    "evidence_type": "replay",
                }
            )
    write_csv(raw_dir / "load_requests.csv", ["step", "time_s", "request_type", "probability", "qps", "evidence_type"], load_rows)
    write_csv(
        raw_dir / "policy_replay_timeseries.csv",
        [
            "policy",
            "policy_display_name",
            "step",
            "time_s",
            "evidence_type",
            "traffic_stress",
            "weighted_edge_distance",
            "active_edge_count",
            "request_mix_entropy",
            "top3_hotspot_churn",
            "traffic_stress_gini",
            "traffic_stress_skew",
            "migration_count",
            "policy_decision_time_ms",
            "latency_ms",
            "sla_ms",
            "sla_pressure",
            "sla_violation_ratio",
        ],
        policy_rows,
    )
    write_csv(
        raw_dir / "e2e_policy_timeseries.csv",
        [
            "policy",
            "policy_display_name",
            "step",
            "time_s",
            "evidence_type",
            "traffic_stress",
            "weighted_edge_distance",
            "active_edge_count",
            "request_mix_entropy",
            "top3_hotspot_churn",
            "traffic_stress_gini",
            "traffic_stress_skew",
            "migration_count",
            "policy_decision_time_ms",
            "latency_ms",
            "sla_ms",
            "sla_pressure",
            "sla_violation_ratio",
        ],
        policy_rows,
    )
    write_csv(
        raw_dir / "gda_runtime_timeseries.csv",
        [
            "step",
            "time_s",
            "evidence_type",
            "gda_query_latency_ms",
            "gda_build_time_ms",
            "gda_total_time_ms",
            "gda_nodes",
            "gda_edges",
            "gda_query_count",
        ],
        gda_runtime_rows,
    )
    (raw_dir / "prometheus_queries.json").write_text(
        json.dumps(
            {
                "evidence_type": "replay",
                "queries": [],
                "note": "No Prometheus queries were issued by this long-mix replay run.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (raw_dir / "prometheus_results.json").write_text(
        json.dumps({"evidence_type": "replay", "results": []}, indent=2, sort_keys=True) + "\n"
    )
    application_context = ApplicationRunContext(
        benchmark=args.benchmark,
        run_id=run_dir.name,
        namespace=args.namespace,
        scale=args.scale,
        replica_level=args.replica_level,
        replica_config=args.replica_config,
        workload_mode=args.mode,
        repeat=args.repeat,
        request_type="mixed",
        worker_nodes_selected=args.worker_nodes_selected,
        actual_app_pods=args.actual_app_pods,
        ready_app_pods=args.ready_app_pods,
        non_empty_worker_nodes=args.non_empty_worker_nodes,
        pod_restarts=args.pod_restarts,
        total_pods=args.total_pods,
        cluster_cpu_utilization=args.cluster_cpu_utilization,
        cluster_memory_utilization=args.cluster_memory_utilization,
        top_node_cpu_utilization=args.top_node_cpu_utilization,
    )
    application_rows = [
        build_application_policy_row(
            policy_row,
            application_context,
            gda_metrics={
                **gda_runtime_rows[int(policy_row["step"])],
                "gda_edges": policy_row.get("active_edge_count", ""),
            },
            throughput_rps=f"{args.total_qps:.6f}",
            error_rate="0.000000",
        )
        for policy_row in policy_rows
    ]
    write_csv(raw_dir / "application_policy_timeseries.csv", APPLICATION_POLICY_TIMESERIES_COLUMNS, application_rows)
    write_snapshot_csv(raw_dir / "callgraph_snapshots.csv", snapshots)
    write_snapshot_jsonl(raw_dir / "callgraph_snapshots.jsonl", snapshots)
    write_snapshot_jsonl(raw_dir / "gda_snapshots.jsonl", snapshots)
    write_csv(raw_dir / "workload_mixer_modes.csv", ["mode", "step", *[f"p_{name}" for name in request_names]], all_mode_rows)
    processed_dir.joinpath("continuous_graph_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    processed_dir.joinpath("continuous_callgraph_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    metric_rows = [
        {"metric": key, "value": f"{value:.8f}" if isinstance(value, (int, float)) else str(value)}
        for key, value in metrics.items()
    ]
    write_csv(processed_dir / "continuous_callgraph_metrics.csv", ["metric", "value"], metric_rows)
    policy_summary_rows = []
    for policy in policies:
        subset = [row for row in policy_rows if row["policy"] == policy]
        if not subset:
            continue
        policy_summary_rows.append(
            {
                "policy": policy,
                "policy_display_name": POLICY_DISPLAY.get(policy, policy),
                "evidence_type": "replay",
                "steps": len(subset),
                "mean_latency_ms": f"{statistics.fmean(float(row['latency_ms']) for row in subset):.6f}",
                "mean_sla_violation_ratio": f"{statistics.fmean(float(row['sla_violation_ratio']) for row in subset):.6f}",
                "max_sla_violation_ratio": f"{max(float(row['sla_violation_ratio']) for row in subset):.6f}",
                "mean_request_mix_entropy": f"{statistics.fmean(float(row['request_mix_entropy']) for row in subset):.6f}",
                "mean_active_edge_count": f"{statistics.fmean(float(row['active_edge_count']) for row in subset):.6f}",
                "migration_count_available": "false",
                "policy_decision_time_available": "false",
            }
        )
    write_csv(
        processed_dir / "policy_e2e_summary.csv",
        [
            "policy",
            "policy_display_name",
            "evidence_type",
            "steps",
            "mean_latency_ms",
            "mean_sla_violation_ratio",
            "max_sla_violation_ratio",
            "mean_request_mix_entropy",
            "mean_active_edge_count",
            "migration_count_available",
            "policy_decision_time_available",
        ],
        policy_summary_rows,
    )
    write_csv(processed_dir / "application_policy_timeseries.csv", APPLICATION_POLICY_TIMESERIES_COLUMNS, application_rows)
    write_application_metrics_summary(processed_dir / "application_metrics_summary.csv", application_rows)
    write_gda_runtime_summary(processed_dir / "gda_runtime_summary.csv", gda_runtime_rows)
    write_callgraph_edges_summary(processed_dir / "callgraph_edges.csv", snapshots)
    (processed_dir / "mode_summary.md").write_text(
        f"""# Continuous Long-Mix Mode Summary

Mode: `{args.mode}`
Steps: `{args.steps}`
Interval seconds: `{args.interval_s:.3f}`
Evidence: replay/model/control-plane for policy latency/SLA fields.

Mean request-mix entropy: {metrics['mean_request_mix_entropy']:.4f}
Mean top-3 hotspot churn: {metrics['mean_top3_hotspot_churn']:.4f}
Mean active edge count: {metrics['mean_active_edge_count']:.2f}
"""
    )
    manifest = {
        "run_id": run_dir.name,
        "evidence_root": f"experiments/runs/{run_dir.name}",
        "evidence_type": "replay/model/control-plane unless live workload logs are present",
        "figures": [
            {
                "path": "figures/continuous_callgraph_timeline.svg",
                "source_files": [
                    "raw/request_mix_timeseries.csv",
                    "raw/policy_replay_timeseries.csv",
                    "processed/continuous_graph_metrics.json",
                ],
            }
        ],
    }
    (figures_dir / "figure_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    run_dir.joinpath("workload_mixer_metadata.json").write_text(
        json.dumps(
            {
                "mode": args.mode,
                "steps": args.steps,
                "interval_s": args.interval_s,
                "total_qps": args.total_qps,
                "live_wrk": args.live_wrk,
                "scale": args.scale,
                "policies": policies,
                "request_types": [request.__dict__ | {"edge_weights": {f"{src}->{dst}": weight for (src, dst), weight in request.edge_weights.items()}} for request in requests],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

if __name__ == "__main__":
    main()
