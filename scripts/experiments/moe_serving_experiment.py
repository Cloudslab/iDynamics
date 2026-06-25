#!/usr/bin/env python3
"""MoE serving generality experiment and placement comparison."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import subprocess
from pathlib import Path
from typing import Mapping

from idynamics.workloads.moe import latency_model, placement_cost, policy_placement, traffic_edges, weights_for_step


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--experts", type=int, default=6)
    parser.add_argument("--steps", type=int, default=48)
    parser.add_argument("--requests-per-step", type=int, default=60)
    parser.add_argument("--nodes", type=int, default=5)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--skew-mode", choices=["stable", "sinusoidal", "phase-shift", "burst"], default="phase-shift")
    parser.add_argument("--zipf-alpha", type=float, default=1.2)
    parser.add_argument("--compute-delay-ms", type=float, default=5.0)
    parser.add_argument("--payload-bytes", type=int, default=256)
    parser.add_argument("--cache-hit-ratio", type=float, default=0.25)
    parser.add_argument("--policies", nargs="+", default=["default", "policy2", "policy3", "policy4"])
    parser.add_argument("--scale-label", default="")
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--image", default="moe-serving:latest")
    parser.add_argument("--live-k8s", action="store_true")
    return parser.parse_args()


def write_csv(path: Path, rows: list[Mapping[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)



def render_manifest(repo_root: Path, run_dir: Path, args: argparse.Namespace, policy: str) -> Path:
    output = run_dir / "raw" / f"moe_{policy}.yaml"
    command = [
        "python3",
        str(repo_root / "examples/moe-serving/k8s/render_manifests.py"),
        "--experts",
        str(args.experts),
        "--policy",
        policy,
        "--image",
        args.image,
        "--compute-delay-ms",
        str(args.compute_delay_ms),
        "--payload-bytes",
        str(args.payload_bytes),
        "--cache-hit-ratio",
        str(args.cache_hit_ratio),
        "--output",
        str(output),
    ]
    if args.scale_label:
        command.extend(["--node-pool-label", args.scale_label])
    subprocess.run(command, check=True)
    return output



def main() -> None:
    args = parse_args()
    if args.experts < 1:
        raise SystemExit("--experts must be >= 1")
    if args.nodes < 1:
        raise SystemExit("--nodes must be >= 1")

    run_dir = Path(args.run_dir)
    raw = run_dir / "raw"
    processed = run_dir / "processed"
    figures = run_dir / "figures"
    for directory in (raw, processed, figures):
        directory.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]

    real_benchmark = {
        "status": "not_available_locally",
        "reason": "No local DeathStarBench Hotel/Media or TrainTicket checkout/manifests were found under /home/ubuntu during this run; the stable MoE microbenchmark path was used.",
    }
    raw.joinpath("real_benchmark_inspection.json").write_text(json.dumps(real_benchmark, indent=2, sort_keys=True) + "\n")

    manifests = {policy: render_manifest(repo_root, run_dir, args, policy) for policy in args.policies}

    rng = random.Random(args.seed)
    rows = []
    for step in range(args.steps):
        weights = weights_for_step(args.experts, step, args.steps, args.skew_mode, args.zipf_alpha)
        edges = traffic_edges(weights, args.requests_per_step, args.top_k, args.payload_bytes)
        placements = {policy: policy_placement(policy, args.experts, args.nodes, weights, args.top_k) for policy in args.policies}
        default_placement_for_step = placements.get("default") or policy_placement("default", args.experts, args.nodes, weights, args.top_k)
        default_cost = placement_cost(edges, default_placement_for_step)
        row = {
            "step": step,
            "hot_expert": max(range(args.experts), key=lambda idx: weights[idx]),
            "expert_popularity": ";".join(f"{weight:.6f}" for weight in weights),
        }
        for policy, placement in placements.items():
            cost = placement_cost(edges, placement)
            latency = latency_model(cost, default_cost, args.compute_delay_ms, rng)
            row[f"{policy}_cost"] = f"{cost:.6f}"
            row[f"{policy}_cost_reduction_pct"] = f"{100.0 * (default_cost - cost) / max(1.0, default_cost):.6f}"
            row[f"{policy}_latency_ms"] = f"{latency:.6f}"
        rows.append(row)

    metrics = {}
    for policy in args.policies:
        metrics[f"mean_{policy}_cost"] = statistics.fmean(float(row[f"{policy}_cost"]) for row in rows)
        metrics[f"mean_{policy}_latency_ms"] = statistics.fmean(float(row[f"{policy}_latency_ms"]) for row in rows)
        metrics[f"mean_{policy}_cost_reduction_pct"] = statistics.fmean(float(row[f"{policy}_cost_reduction_pct"]) for row in rows)
        metrics[f"manifest_{policy}_bytes"] = float(manifests[policy].stat().st_size)
    non_default = [policy for policy in args.policies if policy != "default"]
    best_policy = min(non_default or args.policies, key=lambda policy: metrics[f"mean_{policy}_cost"])
    metrics["best_policy"] = best_policy
    metrics["best_cost_reduction_pct"] = metrics[f"mean_{best_policy}_cost_reduction_pct"]
    metrics["best_latency_ms"] = metrics[f"mean_{best_policy}_latency_ms"]

    write_csv(raw / "moe_expert_skew_timeseries.csv", rows)
    processed.joinpath("moe_placement_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    write_csv(
        processed / "moe_placement_metrics.csv",
        [{"metric": key, "value": f"{value:.8f}" if isinstance(value, float) else str(value)} for key, value in metrics.items()],
    )

    run_dir.joinpath("moe_serving_metadata.json").write_text(
        json.dumps(
            {
                "architecture": "frontend -> tokenizer -> router/gate -> expert-0..expert-k -> aggregator -> cache/state",
                "experts": args.experts,
                "steps": args.steps,
                "requests_per_step": args.requests_per_step,
                "nodes": args.nodes,
                "top_k": args.top_k,
                "skew_mode": args.skew_mode,
                "compute_delay_ms": args.compute_delay_ms,
                "payload_bytes": args.payload_bytes,
                "cache_hit_ratio": args.cache_hit_ratio,
                "policies": args.policies,
                "scale_label": args.scale_label,
                "live_k8s": args.live_k8s,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

if __name__ == "__main__":
    main()
