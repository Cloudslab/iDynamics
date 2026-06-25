#!/usr/bin/env python3
"""Run worker-pool physical Social Network-compatible scale experiments.

This runner is intentionally conservative: it uses the repository's
DeathStarBench-compatible Social Network smoke service graph, short load
windows, worker-only node selectors, and static placement policies. 
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.benchmark_deployment import ExperimentLock, percentile, sh, write
from scripts.experiments.live_network_dynamics import (
    collect_ns,
    run_load,
    selected_nodes,
    social_manifest,
)


RUNS_DIR = REPO_ROOT / "experiments" / "runs"
SCALES = ("scale5", "scale10", "scale20", "scale30", "scale45")
POLICIES = ("kubernetes", "policy1")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_logged(
    run_dir: Path,
    cmd: list[str],
    *,
    timeout: int = 120,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return sh(cmd, run_dir=run_dir, cwd=REPO_ROOT, timeout=timeout, check=check, input_text=input_text)


def init_run(run_id: str, args: argparse.Namespace) -> Path:
    run_dir = RUNS_DIR / run_id
    for sub in ("env", "raw", "processed", "figures", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    write(run_dir / "commands.log", "")
    write(run_dir / "codex_model.txt", os.environ.get("CODEX_MODEL", "codex-cli-local") + "\n")
    write(run_dir / "git_sha.txt", sh(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=False).stdout or "no-git-sha\n")
    write(run_dir / "git_status.txt", sh(["git", "status", "--short", "--branch"], cwd=REPO_ROOT, check=False).stdout)
    config = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "physical_social_network_scale_baseline_vs_policy1",
        "benchmark": "social-network-compatible-smoke",
        "scales": args.scales,
        "policies": list(POLICIES),
        "requests_per_policy": args.requests,
        "concurrency": args.concurrency,
        "sla_ms": args.sla_ms,
        "ready_timeout_s": args.ready_timeout,
        "image": args.image,
        "worker_only": True,
        "tc_impairment": False,
        "repetitions": args.repetitions,
        "duration_rationale": "short request windows per policy/repetition to avoid exhausting the shared 45-worker cluster while still collecting repeated samples",
    }
    write(run_dir / "config.yaml", "\n".join(f"{key}: {json.dumps(value)}" for key, value in config.items()) + "\n")
    for rel, cmd in {
        "env/kubernetes_version.txt": ["kubectl", "version", "-o", "yaml"],
        "env/nodes_wide.txt": ["kubectl", "get", "nodes", "-o", "wide", "--show-labels"],
        "env/pods_all_namespaces_wide.txt": ["kubectl", "get", "pods", "-A", "-o", "wide"],
        "env/services_all_namespaces.txt": ["kubectl", "get", "svc", "-A"],
        "env/node_capacities.json": ["kubectl", "get", "nodes", "-o", "json"],
        "env/metrics_api_top_nodes.txt": ["kubectl", "top", "nodes"],
    }.items():
        result = run_logged(run_dir, cmd, timeout=90, check=False)
        write(run_dir / rel, result.stdout)
        if result.stderr:
            write(run_dir / f"{rel}.err", result.stderr)
    return run_dir


def count_pod_nodes(run_dir: Path, path: Path) -> tuple[int, int]:
    data = json.loads(path.read_text())
    nodes = {
        item.get("spec", {}).get("nodeName")
        for item in data.get("items", [])
        if item.get("spec", {}).get("nodeName")
    }
    return len(data.get("items", [])), len(nodes)


def pod_schedule_latency_ms(path: Path) -> float | None:
    data = json.loads(path.read_text())
    latencies: list[float] = []
    for item in data.get("items", []):
        created = item.get("metadata", {}).get("creationTimestamp")
        scheduled = None
        for condition in item.get("status", {}).get("conditions", []):
            if condition.get("type") == "PodScheduled" and condition.get("status") == "True":
                scheduled = condition.get("lastTransitionTime")
                break
        if not created or not scheduled:
            continue
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        scheduled_dt = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
        latencies.append((scheduled_dt - created_dt).total_seconds() * 1000.0)
    return statistics.median(latencies) if latencies else None


def read_load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def enrich_metrics(
    run_dir: Path,
    scale: str,
    policy: str,
    repetition: int,
    base: dict[str, Any],
    sla_ms: float,
    scheduler_ready_s: float,
) -> dict[str, Any]:
    prefix = f"{scale}_{policy}_rep{repetition:02d}"
    rows = read_load_rows(run_dir / "raw" / f"{prefix}_loadgen.csv")
    latencies = [float(row["latency_ms"]) for row in rows if int(row["status"]) == 200]
    sla_violations = sum(1 for latency in latencies if latency > sla_ms)
    pods_path = run_dir / "raw" / f"{prefix}_after_pods.json"
    pod_count, distinct_nodes = count_pod_nodes(run_dir, pods_path)
    return {
        **base,
        "scale": scale,
        "policy": policy,
        "repetition": repetition,
        "sla_ms": sla_ms,
        "sla_violations": sla_violations,
        "sla_violation_rate": (sla_violations / len(latencies)) if latencies else 0.0,
        "scheduler_decision_time_ms": pod_schedule_latency_ms(pods_path),
        "rollout_ready_time_ms": scheduler_ready_s * 1000.0,
        "gda_build_time_ms": None,
        "migration_count": 0,
        "network_target_vs_measured_error": None,
        "pod_count": pod_count,
        "distinct_worker_nodes_used": distinct_nodes,
        "observed_cpu_memory_status": "unavailable: Kubernetes Metrics API was not available; see env/metrics_api_top_nodes.txt.err",
    }


def bootstrap_mean_ci(values: list[float], *, seed: int, resamples: int = 5000) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "stddev": None, "ci95_low": None, "ci95_high": None, "n": 0}
    mean = statistics.fmean(values)
    if len(values) == 1:
        return {"mean": mean, "stddev": 0.0, "ci95_low": None, "ci95_high": None, "n": 1}
    stddev = statistics.stdev(values)
    rng = random.Random(seed)
    boot_means = []
    for _ in range(resamples):
        sample = [values[rng.randrange(len(values))] for _ in values]
        boot_means.append(statistics.fmean(sample))
    return {
        "mean": mean,
        "stddev": stddev,
        "ci95_low": percentile(boot_means, 2.5),
        "ci95_high": percentile(boot_means, 97.5),
        "n": len(values),
    }


def aggregate_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in metrics:
        grouped.setdefault((item["scale"], item["policy"]), []).append(item)

    aggregate: list[dict[str, Any]] = []
    fields = (
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "throughput_rps",
        "sla_violations",
        "sla_violation_rate",
        "scheduler_decision_time_ms",
        "rollout_ready_time_ms",
        "success",
        "errors",
    )
    for (scale, policy), items in sorted(grouped.items()):
        row: dict[str, Any] = {
            "scale": scale,
            "policy": policy,
            "repetitions": len(items),
            "requests_per_repetition": items[0].get("requests") if items else None,
            "sla_ms": items[0].get("sla_ms") if items else None,
            "pod_count_mean": statistics.fmean(item["pod_count"] for item in items),
            "distinct_worker_nodes_used_mean": statistics.fmean(item["distinct_worker_nodes_used"] for item in items),
        }
        for field in fields:
            values = [float(item[field]) for item in items if item.get(field) is not None]
            seed = sum(ord(ch) for ch in f"{scale}:{policy}:{field}")
            stats = bootstrap_mean_ci(values, seed=seed)
            for suffix, value in stats.items():
                row[f"{field}_{suffix}"] = value
        aggregate.append(row)
    return aggregate


def policy_deltas(aggregate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_scale_policy = {(row["scale"], row["policy"]): row for row in aggregate}
    deltas: list[dict[str, Any]] = []
    for scale in sorted({row["scale"] for row in aggregate}):
        base = by_scale_policy.get((scale, "kubernetes"))
        p1 = by_scale_policy.get((scale, "policy1"))
        if not base or not p1:
            continue
        row: dict[str, Any] = {"scale": scale, "baseline": "kubernetes", "policy": "policy1"}
        for field in ("p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "throughput_rps", "sla_violations", "sla_violation_rate"):
            b = base.get(f"{field}_mean")
            p = p1.get(f"{field}_mean")
            if b in (None, 0) or p is None:
                row[f"{field}_absolute_delta"] = None
                row[f"{field}_percent_delta_vs_kubernetes"] = None
            else:
                row[f"{field}_absolute_delta"] = p - b
                row[f"{field}_percent_delta_vs_kubernetes"] = ((p - b) / b) * 100.0
        deltas.append(row)
    return deltas


def write_aggregate_csv(run_dir: Path, filename: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        write(run_dir / "processed" / filename, "")
        return
    fields = sorted({key for item in rows for key in item})
    with (run_dir / "processed" / filename).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_standard_metrics(run_dir: Path, metrics: list[dict[str, Any]], aggregate: list[dict[str, Any]]) -> None:
    rows = []
    metric_specs = {
        "latency_p50_ms": ("p50_latency_ms", "ms"),
        "latency_p95_ms": ("p95_latency_ms", "ms"),
        "latency_p99_ms": ("p99_latency_ms", "ms"),
        "throughput_rps": ("throughput_rps", "requests/s"),
        "sla_violations": ("sla_violations", "count"),
        "sla_violation_rate": ("sla_violation_rate", "ratio"),
        "scheduler_decision_time_ms": ("scheduler_decision_time_ms", "ms"),
        "gda_build_time_ms": ("gda_build_time_ms", "ms"),
        "cpu_overhead_pct": (None, "percent"),
        "memory_overhead_mb": (None, "MiB"),
        "migration_count": ("migration_count", "count"),
        "network_target_vs_measured_error": ("network_target_vs_measured_error", "unitless"),
    }
    for item in aggregate:
        policy = f"{item['scale']}-{item['policy']}"
        for metric, (source_key, unit) in metric_specs.items():
            value = item.get(f"{source_key}_mean") if source_key else None
            rows.append(
                {
                    "run_id": run_dir.name,
                    "experiment_type": "physical_social_scale",
                    "policy": policy,
                    "metric": metric,
                    "value": value,
                    "unit": unit,
                    "source_file": "processed/physical_social_aggregate_metrics.json" if source_key else "",
                    "source_column": f"{source_key}_mean" if source_key else "",
                    "status": "measured" if source_key and value is not None else "unavailable",
                    "notes": f"mean across {item['repetitions']} repetitions; 95% CI in processed aggregate CSV" if source_key and value is not None else "static placement; no live tc impairment" if metric in {"migration_count", "network_target_vs_measured_error"} else "",
                }
            )
    write(run_dir / "processed" / "standard_metrics.json", json.dumps({"metrics": rows}, indent=2, sort_keys=True) + "\n")
    with (run_dir / "processed" / "standard_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)


def write_standard_summary_table(run_dir: Path, aggregate: list[dict[str, Any]]) -> None:
    lines = [
        f"# Standard Evaluation Summary: {run_dir.name}",
        "",
        f"Source run ledger: `{run_dir}`",
        "",
        "| Scale | Policy | Reps | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | SLA violation rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    csv_rows = []
    for item in aggregate:
        lines.append(
            f"| {item['scale']} | {item['policy']} | {item['repetitions']} | "
            f"{fmt_ci(item, 'p50_latency_ms')} | {fmt_ci(item, 'p95_latency_ms')} | {fmt_ci(item, 'p99_latency_ms')} | "
            f"{fmt_ci(item, 'throughput_rps')} | {fmt_ci(item, 'sla_violations')} | {fmt_ci(item, 'sla_violation_rate', 4)} |"
        )
        csv_rows.append(
            {
                "scale": item["scale"],
                "policy": item["policy"],
                "repetitions": item["repetitions"],
                "p50_latency_ms": item["p50_latency_ms_mean"],
                "p95_latency_ms": item["p95_latency_ms_mean"],
                "p99_latency_ms": item["p99_latency_ms_mean"],
                "throughput_rps": item["throughput_rps_mean"],
                "sla_violations": item["sla_violations_mean"],
                "sla_violation_rate": item["sla_violation_rate_mean"],
                "source_file": "processed/physical_social_aggregate_metrics.csv",
            }
        )

    write(run_dir / "processed" / "standard_summary_table.md", "\n".join(lines))
    with (run_dir / "processed" / "standard_summary_table.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in csv_rows for key in row}))
        writer.writeheader()
        writer.writerows(csv_rows)


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def fmt_ci(row: dict[str, Any], field: str, digits: int = 2) -> str:
    mean = row.get(f"{field}_mean")
    low = row.get(f"{field}_ci95_low")
    high = row.get(f"{field}_ci95_high")
    if low is None or high is None:
        return fmt(mean, digits)
    return f"{fmt(mean, digits)} [{fmt(low, digits)}, {fmt(high, digits)}]"



def write_csv(run_dir: Path, metrics: list[dict[str, Any]]) -> None:
    fields = sorted({key for item in metrics for key in item})
    with (run_dir / "processed" / "physical_social_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(metrics)


def run_scale_policy(run_dir: Path, scale: str, policy: str, repetition: int, args: argparse.Namespace) -> dict[str, Any]:
    short_policy = "k8s" if policy == "kubernetes" else "p1"
    stamp = run_dir.name.rsplit("-", 1)[-1].lower().replace("t", "")
    prefix = f"{scale}_{policy}_rep{repetition:02d}"
    namespace = f"pss-{stamp}-{scale.replace('scale', 's')}-{short_policy}-r{repetition:02d}"
    manifest = social_manifest(namespace, scale, args.image, policy)
    write(run_dir / "raw" / f"{prefix}_manifest.yaml", manifest)
    start = time.perf_counter()
    try:
        apply = run_logged(run_dir, ["kubectl", "apply", "-f", "-"], timeout=120, check=False, input_text=manifest)
        write(run_dir / "logs" / f"{prefix}_apply.stdout", apply.stdout)
        write(run_dir / "logs" / f"{prefix}_apply.stderr", apply.stderr)
        if apply.returncode != 0:
            raise RuntimeError(apply.stderr)
        run_logged(
            run_dir,
            ["kubectl", "-n", namespace, "wait", "--for=condition=available", "deployment", "--all", f"--timeout={args.ready_timeout}s"],
            timeout=args.ready_timeout + 60,
        )
        ready_s = time.perf_counter() - start
        collect_ns(run_dir, namespace, f"{prefix}_ready")
        metrics = run_load(run_dir, namespace, policy, args.requests, args.concurrency)
        generic_load = run_dir / "raw" / f"{policy}_loadgen.csv"
        if generic_load.exists():
            shutil.copyfile(generic_load, run_dir / "raw" / f"{prefix}_loadgen.csv")
        collect_ns(run_dir, namespace, f"{prefix}_after")
        return enrich_metrics(run_dir, scale, policy, repetition, metrics, args.sla_ms, ready_s)
    finally:
        if not args.keep:
            run_logged(run_dir, ["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], timeout=60, check=False)


def run(args: argparse.Namespace) -> Path:
    prefix = "physical-social-repeated-scale-series" if args.repetitions > 1 else "physical-social-scale-series"
    run_id = args.run_id or f"{prefix}-{utc_stamp()}"
    run_dir = init_run(run_id, args)
    metrics: list[dict[str, Any]] = []
    with ExperimentLock(run_id):
        selected: dict[str, list[dict[str, str]]] = {}
        for scale in args.scales:
            selected[scale] = selected_nodes(scale)
        write(run_dir / "raw" / "selected_nodes.json", json.dumps(selected, indent=2) + "\n")
        for scale in args.scales:
            for policy in POLICIES:
                for repetition in range(1, args.repetitions + 1):
                    metrics.append(run_scale_policy(run_dir, scale, policy, repetition, args))
                    write(run_dir / "processed" / "physical_social_metrics.json", json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    write_csv(run_dir, metrics)
    aggregate = aggregate_metrics(metrics)
    deltas = policy_deltas(aggregate)
    write(run_dir / "processed" / "physical_social_aggregate_metrics.json", json.dumps(aggregate, indent=2, sort_keys=True) + "\n")
    write(run_dir / "processed" / "physical_social_policy_deltas.json", json.dumps(deltas, indent=2, sort_keys=True) + "\n")
    write_aggregate_csv(run_dir, "physical_social_aggregate_metrics.csv", aggregate)
    write_aggregate_csv(run_dir, "physical_social_policy_deltas.csv", deltas)
    write_standard_metrics(run_dir, metrics, aggregate)
    write_standard_summary_table(run_dir, aggregate)
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scales", nargs="+", choices=SCALES, default=list(SCALES))
    parser.add_argument("--requests", type=int, default=90)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--sla-ms", type=float, default=150.0)
    parser.add_argument("--ready-timeout", type=int, default=240)
    parser.add_argument("--image", default="python:3.11-slim")
    parser.add_argument("--run-id")
    parser.add_argument("--keep", action="store_true")
    return parser.parse_args()


def main() -> int:
    path = run(parse_args())
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
