#!/usr/bin/env python3
"""Normalize experiment metrics into a common schema.

The script reads data under experiments/runs/<run_id>.  Missing metrics are kept as explicit null values with unavailable status.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = REPO_ROOT / "experiments" / "runs"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.stats_helpers import numeric, percentile

STANDARD_METRICS = [
    ("latency_p50_ms", "ms"),
    ("latency_p95_ms", "ms"),
    ("latency_p99_ms", "ms"),
    ("throughput_rps", "requests/s"),
    ("sla_violations", "count"),
    ("sla_violation_rate", "ratio"),
    ("scheduler_decision_time_ms", "ms"),
    ("gda_build_time_ms", "ms"),
    ("ndm_injection_time_ms", "ms"),
    ("cpu_overhead_pct", "percent"),
    ("memory_overhead_mb", "MiB"),
    ("migration_count", "count"),
    ("network_target_vs_measured_error", "unitless"),
    ("placement_cost_reduction_pct", "percent"),
]


@dataclass
class MetricRow:
    run_id: str
    experiment_type: str
    policy: str
    metric: str
    value: float | None
    unit: str
    source_file: str
    source_column: str
    status: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_type": self.experiment_type,
            "policy": self.policy,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "source_file": self.source_file,
            "source_column": self.source_column,
            "status": self.status,
            "notes": self.notes,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--run-id", help="Run id under experiments/runs/")
    selector.add_argument("--run-dir", help="Path to experiments/runs/<run_id>")
    parser.add_argument("--output-name", default="standard_metrics")
    return parser.parse_args()


def resolve_run_dir(args: argparse.Namespace) -> Path:
    run_dir = (RUNS_ROOT / args.run_id) if args.run_id else Path(args.run_dir).resolve()
    try:
        run_dir.relative_to(RUNS_ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(f"refusing to collect metrics outside {RUNS_ROOT}: {run_dir}") from exc
    if not run_dir.is_dir():
        raise SystemExit(f"run ledger not found: {run_dir}")
    required = ["config.yaml", "git_sha.txt", "git_status.txt", "codex_model.txt", "commands.log", "summary.md"]
    missing = [name for name in required if not (run_dir / name).exists()]
    if missing:
        raise SystemExit(f"run ledger {run_dir.name} is missing required files: {', '.join(missing)}")
    if not (run_dir / "raw").is_dir():
        raise SystemExit(f"run ledger {run_dir.name} has no raw/ directory")
    return run_dir


def experiment_type(run_id: str) -> str:
    if run_id.startswith("physical-moe"):
        return "physical_moe"
    if run_id.startswith("moe-serving"):
        return "moe_serving_control_plane"
    if run_id.startswith("gda-overhead") or run_id.startswith("gda-scalability"):
        return "gda_overhead_synthetic"
    if run_id.startswith("network-trace"):
        return "network_trace_replay"
    if run_id.startswith("continuous-callgraph"):
        return "continuous_callgraph"
    if run_id.startswith("physical-social-scale-series"):
        return "physical_social_scale"
    if run_id.startswith("live-tc-social"):
        return "live_tc_social"
    if run_id.startswith("live-tc-validation"):
        return "live_tc_validation"
    if run_id.startswith("mesh-overhead"):
        return "mesh_overhead"
    if run_id.startswith("policy-smoke"):
        return "policy_smoke"
    if run_id.startswith("observability"):
        return "observability"
    return "unknown"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def mean(values: Iterable[float]) -> float | None:
    vals = list(values)
    return statistics.fmean(vals) if vals else None


def base_rows(run_id: str, exp_type: str, policies: Iterable[str]) -> dict[tuple[str, str], MetricRow]:
    rows: dict[tuple[str, str], MetricRow] = {}
    for policy in policies:
        for metric, unit in STANDARD_METRICS:
            rows[(policy, metric)] = MetricRow(
                run_id=run_id,
                experiment_type=exp_type,
                policy=policy,
                metric=metric,
                value=None,
                unit=unit,
                source_file="",
                source_column="",
                status="unavailable",
                notes="metric not emitted by this run type",
            )
    return rows


def set_metric(
    rows: dict[tuple[str, str], MetricRow],
    policy: str,
    metric: str,
    value: float | None,
    source_file: str,
    source_column: str,
    notes: str = "",
) -> None:
    row = rows[(policy, metric)]
    row.value = value
    row.source_file = source_file
    row.source_column = source_column
    row.status = "measured" if value is not None else "not_applicable"
    row.notes = notes


def collect_physical_moe(run_dir: Path) -> list[MetricRow]:
    run_id = run_dir.name
    exp_type = experiment_type(run_id)
    data_path = run_dir / "processed" / "physical_moe_metrics.json"
    if not data_path.exists():
        raise SystemExit(f"{run_id} is missing {data_path.relative_to(run_dir)}")
    data = read_json(data_path)
    policies = list(data)
    rows = base_rows(run_id, exp_type, policies)
    for policy, item in data.items():
        requests = numeric(item.get("requests")) or 0.0
        sla_violations = numeric(item.get("sla_violations"))
        set_metric(rows, policy, "latency_p50_ms", numeric(item.get("p50_latency_ms")), "processed/physical_moe_metrics.json", "p50_latency_ms")
        set_metric(rows, policy, "latency_p95_ms", numeric(item.get("p95_latency_ms")), "processed/physical_moe_metrics.json", "p95_latency_ms")
        set_metric(rows, policy, "latency_p99_ms", numeric(item.get("p99_latency_ms")), "processed/physical_moe_metrics.json", "p99_latency_ms")
        set_metric(rows, policy, "throughput_rps", numeric(item.get("throughput_rps")), "processed/physical_moe_metrics.json", "throughput_rps")
        set_metric(rows, policy, "sla_violations", sla_violations, "processed/physical_moe_metrics.json", "sla_violations")
        set_metric(rows, policy, "sla_violation_rate", (sla_violations / requests) if requests > 0 and sla_violations is not None else None, "processed/physical_moe_metrics.json", "sla_violations/requests")
        set_metric(rows, policy, "scheduler_decision_time_ms", (numeric(item.get("scheduler_ready_s")) or 0.0) * 1000.0, "processed/physical_moe_metrics.json", "scheduler_ready_s", "apply-to-Available time")
        set_metric(rows, policy, "gda_build_time_ms", numeric(item.get("gda_build_time_ms")), "processed/physical_moe_metrics.json", "gda_build_time_ms")
        set_metric(rows, policy, "migration_count", numeric(item.get("migration_count")), "processed/physical_moe_metrics.json", "migration_count")
        set_metric(rows, policy, "network_target_vs_measured_error", numeric(item.get("network_target_vs_measured_error")), "processed/physical_moe_metrics.json", "network_target_vs_measured_error", "null means live tc was not applied")
    return list(rows.values())


def collect_moe_control_plane(run_dir: Path) -> list[MetricRow]:
    run_id = run_dir.name
    exp_type = experiment_type(run_id)
    raw_path = run_dir / "raw" / "moe_expert_skew_timeseries.csv"
    if not raw_path.exists():
        raise SystemExit(f"{run_id} is missing {raw_path.relative_to(run_dir)}")
    raw_rows = read_csv(raw_path)
    prefixes = sorted({key.removesuffix("_latency_ms") for key in raw_rows[0] if key.endswith("_latency_ms")})
    label = {"default": "kubernetes-default", "idynamics": "idynamics-hot-path"}
    policies = [label.get(prefix, prefix) for prefix in prefixes]
    rows = base_rows(run_id, exp_type, policies)
    for prefix, policy in zip(prefixes, policies):
        latencies = [value for value in (numeric(row.get(f"{prefix}_latency_ms")) for row in raw_rows) if value is not None]
        reductions = [value for value in (numeric(row.get(f"{prefix}_cost_reduction_pct")) for row in raw_rows) if value is not None]
        set_metric(rows, policy, "latency_p50_ms", percentile(latencies, 50), "raw/moe_expert_skew_timeseries.csv", f"{prefix}_latency_ms")
        set_metric(rows, policy, "latency_p95_ms", percentile(latencies, 95), "raw/moe_expert_skew_timeseries.csv", f"{prefix}_latency_ms")
        set_metric(rows, policy, "latency_p99_ms", percentile(latencies, 99), "raw/moe_expert_skew_timeseries.csv", f"{prefix}_latency_ms")
        set_metric(rows, policy, "placement_cost_reduction_pct", percentile(reductions, 50), "raw/moe_expert_skew_timeseries.csv", f"{prefix}_cost_reduction_pct", "median modeled reduction versus default")
        set_metric(rows, policy, "throughput_rps", numeric(len(raw_rows)), "raw/moe_expert_skew_timeseries.csv", "step", "modeled intervals, not live rps")
    return list(rows.values())


def collect_gda(run_dir: Path) -> list[MetricRow]:
    run_id = run_dir.name
    exp_type = experiment_type(run_id)
    raw_path = run_dir / "raw" / "gda_overhead_repetitions.csv"
    if not raw_path.exists():
        raise SystemExit(f"{run_id} is missing {raw_path.relative_to(run_dir)}")
    raw_rows = read_csv(raw_path)
    if raw_rows and "mode" in raw_rows[0]:
        policies = sorted({row["mode"] for row in raw_rows})
        rows = base_rows(run_id, exp_type, policies)
        for policy in policies:
            policy_rows = [row for row in raw_rows if row["mode"] == policy]
            wall_ms = [value for value in (numeric(row.get("graph_build_wall_ms")) for row in policy_rows) if value is not None]
            cpu_ms = [value for value in (numeric(row.get("graph_build_cpu_ms")) for row in policy_rows) if value is not None]
            memory_mib = [value for value in (numeric(row.get("peak_python_memory_mib")) for row in policy_rows) if value is not None]
            set_metric(rows, policy, "gda_build_time_ms", percentile(wall_ms, 50), "raw/gda_overhead_repetitions.csv", "graph_build_wall_ms", "median graph-build wall time across service sizes and repetitions")
            set_metric(rows, policy, "scheduler_decision_time_ms", percentile(cpu_ms, 50), "raw/gda_overhead_repetitions.csv", "graph_build_cpu_ms", "median local CPU time used as Algorithm 1 control-plane CPU proxy")
            set_metric(rows, policy, "memory_overhead_mb", percentile(memory_mib, 50), "raw/gda_overhead_repetitions.csv", "peak_python_memory_mib", "median peak traced Python allocation")
        return list(rows.values())

    rows = base_rows(run_id, exp_type, ["dense-pair-scan", "sparse-gda"])
    dense_ms = [(numeric(row.get("dense_seconds")) or 0.0) * 1000.0 for row in raw_rows]
    sparse_ms = [(numeric(row.get("sparse_seconds")) or 0.0) * 1000.0 for row in raw_rows]
    set_metric(rows, "dense-pair-scan", "gda_build_time_ms", percentile(dense_ms, 50), "raw/gda_overhead_repetitions.csv", "dense_seconds", "median over all repetitions")
    set_metric(rows, "sparse-gda", "gda_build_time_ms", percentile(sparse_ms, 50), "raw/gda_overhead_repetitions.csv", "sparse_seconds", "median over all repetitions")
    return list(rows.values())


def collect_network_trace(run_dir: Path) -> list[MetricRow]:
    run_id = run_dir.name
    exp_type = experiment_type(run_id)
    data_path = run_dir / "processed" / "network_trace_metrics.json"
    if not data_path.exists():
        raise SystemExit(f"{run_id} is missing {data_path.relative_to(run_dir)}")
    data = read_json(data_path)
    rows = base_rows(run_id, exp_type, data.keys())
    for provider, metrics in data.items():
        latency = metrics.get("latency_ms", {})
        set_metric(rows, provider, "latency_p50_ms", numeric(latency.get("p50")), "processed/network_trace_metrics.json", "latency_ms.p50")
        set_metric(rows, provider, "latency_p95_ms", numeric(latency.get("p95")), "processed/network_trace_metrics.json", "latency_ms.p95")
        set_metric(rows, provider, "latency_p99_ms", numeric(latency.get("p99")), "processed/network_trace_metrics.json", "latency_ms.p99")
    return list(rows.values())


def collect_continuous_callgraph(run_dir: Path) -> list[MetricRow]:
    run_id = run_dir.name
    exp_type = experiment_type(run_id)
    raw_path = run_dir / "raw" / "request_mix_timeseries.csv"
    if not raw_path.exists():
        raise SystemExit(f"{run_id} is missing {raw_path.relative_to(run_dir)}")
    raw_rows = read_csv(raw_path)
    rows = base_rows(run_id, exp_type, ["workload-mixer"])
    latencies = [value for value in (numeric(row.get("latency_ms")) for row in raw_rows) if value is not None]
    sla_values = [numeric(row.get("sla_violation_ratio")) for row in raw_rows]
    qps_values = []
    for row in raw_rows:
        qps_total = sum(numeric(value) or 0.0 for key, value in row.items() if key.startswith("qps_"))
        if qps_total:
            qps_values.append(qps_total)
    set_metric(rows, "workload-mixer", "latency_p50_ms", percentile(latencies, 50), "raw/request_mix_timeseries.csv", "latency_ms")
    set_metric(rows, "workload-mixer", "latency_p95_ms", percentile(latencies, 95), "raw/request_mix_timeseries.csv", "latency_ms")
    set_metric(rows, "workload-mixer", "latency_p99_ms", percentile(latencies, 99), "raw/request_mix_timeseries.csv", "latency_ms")
    set_metric(rows, "workload-mixer", "throughput_rps", mean(qps_values), "raw/request_mix_timeseries.csv", "qps_*", "configured aggregate request rate")
    set_metric(rows, "workload-mixer", "sla_violation_rate", mean(v for v in sla_values if v is not None), "raw/request_mix_timeseries.csv", "sla_violation_ratio")
    return list(rows.values())


def collect_physical_social(run_dir: Path) -> list[MetricRow]:
    data_path = run_dir / "processed" / "physical_social_metrics.json"
    if not data_path.exists():
        raise SystemExit(f"{run_dir.name} is missing {data_path.relative_to(run_dir)}")
    data = read_json(data_path)
    policies = [f"{item['scale']}-{item['policy']}" for item in data]
    rows = base_rows(run_dir.name, experiment_type(run_dir.name), policies)
    for item in data:
        policy = f"{item['scale']}-{item['policy']}"
        set_metric(rows, policy, "latency_p50_ms", numeric(item.get("p50_latency_ms")), "processed/physical_social_metrics.json", "p50_latency_ms")
        set_metric(rows, policy, "latency_p95_ms", numeric(item.get("p95_latency_ms")), "processed/physical_social_metrics.json", "p95_latency_ms")
        set_metric(rows, policy, "latency_p99_ms", numeric(item.get("p99_latency_ms")), "processed/physical_social_metrics.json", "p99_latency_ms")
        set_metric(rows, policy, "throughput_rps", numeric(item.get("throughput_rps")), "processed/physical_social_metrics.json", "throughput_rps")
        set_metric(rows, policy, "sla_violations", numeric(item.get("sla_violations")), "processed/physical_social_metrics.json", "sla_violations")
        set_metric(rows, policy, "sla_violation_rate", numeric(item.get("sla_violation_rate")), "processed/physical_social_metrics.json", "sla_violation_rate")
        set_metric(rows, policy, "scheduler_decision_time_ms", numeric(item.get("scheduler_decision_time_ms")), "processed/physical_social_metrics.json", "scheduler_decision_time_ms")
        set_metric(rows, policy, "gda_build_time_ms", numeric(item.get("gda_build_time_ms")), "processed/physical_social_metrics.json", "gda_build_time_ms")
        set_metric(rows, policy, "migration_count", numeric(item.get("migration_count")), "processed/physical_social_metrics.json", "migration_count")
        set_metric(rows, policy, "network_target_vs_measured_error", numeric(item.get("network_target_vs_measured_error")), "processed/physical_social_metrics.json", "network_target_vs_measured_error")
    return list(rows.values())


def collect_live_tc_social(run_dir: Path) -> list[MetricRow]:
    data_path = run_dir / "processed" / "social_live_tc_metrics.json"
    if not data_path.exists():
        raise SystemExit(f"{run_dir.name} is missing {data_path.relative_to(run_dir)}")
    data = read_json(data_path)["policies"]
    policies = [item["placement"] for item in data]
    rows = base_rows(run_dir.name, experiment_type(run_dir.name), policies)
    for item in data:
        policy = item["placement"]
        requests = numeric(item.get("requests")) or 0.0
        errors = numeric(item.get("errors")) or 0.0
        set_metric(rows, policy, "latency_p50_ms", numeric(item.get("p50_latency_ms")), "processed/social_live_tc_metrics.json", "p50_latency_ms")
        set_metric(rows, policy, "latency_p95_ms", numeric(item.get("p95_latency_ms")), "processed/social_live_tc_metrics.json", "p95_latency_ms")
        set_metric(rows, policy, "latency_p99_ms", numeric(item.get("p99_latency_ms")), "processed/social_live_tc_metrics.json", "p99_latency_ms")
        set_metric(rows, policy, "throughput_rps", numeric(item.get("throughput_rps")), "processed/social_live_tc_metrics.json", "throughput_rps")
        set_metric(rows, policy, "sla_violations", errors, "processed/social_live_tc_metrics.json", "errors")
        set_metric(rows, policy, "sla_violation_rate", (errors / requests) if requests else None, "processed/social_live_tc_metrics.json", "errors/requests")
    return list(rows.values())


def collect_mesh_overhead(run_dir: Path) -> list[MetricRow]:
    data_path = run_dir / "processed" / "mesh_overhead_summary.json"
    if not data_path.exists():
        raise SystemExit(f"{run_dir.name} is missing {data_path.relative_to(run_dir)}")
    data = read_json(data_path)
    policies = [f"{item['scale']}-{item['condition']}" for item in data]
    rows = base_rows(run_dir.name, experiment_type(run_dir.name), policies)
    for item in data:
        policy = f"{item['scale']}-{item['condition']}"
        client_mem = numeric(item.get("client_istio-proxy_memory_mib_mean")) or 0.0
        server_mem = numeric(item.get("server_istio-proxy_memory_mib_mean")) or 0.0
        client_cpu = numeric(item.get("client_istio-proxy_cpu_cores_mean")) or 0.0
        server_cpu = numeric(item.get("server_istio-proxy_cpu_cores_mean")) or 0.0
        set_metric(rows, policy, "latency_p50_ms", numeric(item.get("p50_ms_mean")), "processed/mesh_overhead_summary.json", "p50_ms_mean")
        set_metric(rows, policy, "latency_p95_ms", numeric(item.get("p95_ms_mean")), "processed/mesh_overhead_summary.json", "p95_ms_mean")
        set_metric(rows, policy, "latency_p99_ms", numeric(item.get("p99_ms_mean")), "processed/mesh_overhead_summary.json", "p99_ms_mean")
        set_metric(rows, policy, "throughput_rps", numeric(item.get("throughput_rps_mean")), "processed/mesh_overhead_summary.json", "throughput_rps_mean")
        set_metric(rows, policy, "cpu_overhead_pct", (client_cpu + server_cpu) * 100.0, "processed/mesh_overhead_summary.json", "istio_proxy_cpu_cores_mean", "combined sidecar CPU cores as percent of one core")
        set_metric(rows, policy, "memory_overhead_mb", client_mem + server_mem, "processed/mesh_overhead_summary.json", "istio_proxy_memory_mib_mean", "combined sidecar memory")
    return list(rows.values())


def collect_live_tc_validation(run_dir: Path) -> list[MetricRow]:
    data_path = run_dir / "processed" / "tc_validation_metrics.json"
    if not data_path.exists():
        raise SystemExit(f"{run_dir.name} is missing {data_path.relative_to(run_dir)}")
    data = read_json(data_path)
    rows = base_rows(run_dir.name, experiment_type(run_dir.name), ["tc-validation"])
    set_metric(rows, "tc-validation", "network_target_vs_measured_error", numeric(data.get("target_vs_measured_error_ms")), "processed/tc_validation_metrics.json", "target_vs_measured_error_ms", "absolute RTT error in ms")
    set_metric(rows, "tc-validation", "latency_p50_ms", numeric(data.get("during_mean_rtt_ms")), "processed/tc_validation_metrics.json", "during_mean_rtt_ms", "mean RTT during tc injection")
    set_metric(rows, "tc-validation", "ndm_injection_time_ms", numeric(data.get("target_one_way_delay_ms")), "processed/tc_validation_metrics.json", "target_one_way_delay_ms", "configured one-way qdisc delay")
    return list(rows.values())


def collect_unknown(run_dir: Path) -> list[MetricRow]:
    return list(base_rows(run_dir.name, experiment_type(run_dir.name), ["run"]).values())


def collect(run_dir: Path) -> list[MetricRow]:
    exp_type = experiment_type(run_dir.name)
    if exp_type == "physical_moe":
        return collect_physical_moe(run_dir)
    if exp_type == "moe_serving_control_plane":
        return collect_moe_control_plane(run_dir)
    if exp_type == "gda_overhead_synthetic":
        return collect_gda(run_dir)
    if exp_type == "network_trace_replay":
        return collect_network_trace(run_dir)
    if exp_type == "continuous_callgraph":
        return collect_continuous_callgraph(run_dir)
    if exp_type == "physical_social_scale":
        return collect_physical_social(run_dir)
    if exp_type == "live_tc_social":
        return collect_live_tc_social(run_dir)
    if exp_type == "live_tc_validation":
        return collect_live_tc_validation(run_dir)
    if exp_type == "mesh_overhead":
        return collect_mesh_overhead(run_dir)
    return collect_unknown(run_dir)


def write_outputs(run_dir: Path, rows: list[MetricRow], output_name: str) -> None:
    processed = run_dir / "processed"
    processed.mkdir(exist_ok=True)
    dictionaries = [row.as_dict() for row in rows]
    json_path = processed / f"{output_name}.json"
    csv_path = processed / f"{output_name}.csv"
    json_path.write_text(json.dumps({"run_id": run_dir.name, "metrics": dictionaries}, indent=2, sort_keys=True) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dictionaries[0]))
        writer.writeheader()
        writer.writerows(dictionaries)


def main() -> int:
    args = parse_args()
    run_dir = resolve_run_dir(args)
    rows = collect(run_dir)
    write_outputs(run_dir, rows, args.output_name)
    print(run_dir / "processed" / f"{args.output_name}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
