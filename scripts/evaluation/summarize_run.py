#!/usr/bin/env python3
"""Create a sourced statistical summary table for one run ledger."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = REPO_ROOT / "experiments" / "runs"
COLLECT = REPO_ROOT / "scripts" / "evaluation" / "collect_metrics.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.stats_helpers import deltas, describe, numeric

DISPLAY_METRICS = [
    "latency_p50_ms",
    "latency_p95_ms",
    "latency_p99_ms",
    "throughput_rps",
    "sla_violations",
    "sla_violation_rate",
    "scheduler_decision_time_ms",
    "gda_build_time_ms",
    "ndm_injection_time_ms",
    "cpu_overhead_pct",
    "memory_overhead_mb",
    "migration_count",
    "network_target_vs_measured_error",
    "placement_cost_reduction_pct",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Run id under experiments/runs/")
    parser.add_argument("--refresh", action="store_true", help="Regenerate processed/standard_metrics.* first")
    return parser.parse_args()


def run_dir(run_id: str) -> Path:
    path = RUNS_ROOT / run_id
    if not path.is_dir():
        raise SystemExit(f"run ledger not found: {path}")
    return path


def ensure_standard_metrics(path: Path, refresh: bool) -> Path:
    metrics_path = path / "processed" / "standard_metrics.json"
    if refresh or not metrics_path.exists():
        subprocess.run([sys.executable, str(COLLECT), "--run-id", path.name], cwd=REPO_ROOT, check=True)
    return metrics_path


def load_metrics(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text())["metrics"]


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.2f}"
    if abs(value) >= 10:
        return f"{value:.3f}"
    return f"{value:.4f}"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_detailed_stats(run_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    raw = run_dir / "raw"

    for path in sorted(raw.glob("*_loadgen.csv")):
        rows = read_csv_rows(path)
        latencies = [numeric(row.get("latency_ms")) for row in rows if row.get("status", "200") == "200"]
        source = f"raw/{path.name}"
        name = path.name.removesuffix("_loadgen.csv")
        parts = name.split("_", 1)
        scale = parts[0] if parts and parts[0].startswith("scale") else ""
        policy = parts[1] if scale and len(parts) > 1 else name
        stats = describe(latencies)
        records.append({
            "run_id": run_dir.name,
            "comparison_group": scale or "loadgen",
            "policy": policy,
            "metric": "request_latency_ms",
            "unit": "ms",
            "source_file": source,
            **stats,
        })

    fortio = raw / "fortio_repetitions.csv"
    if fortio.exists():
        rows = read_csv_rows(fortio)
        for scale in sorted({row["scale"] for row in rows}):
            for condition in sorted({row["condition"] for row in rows if row["scale"] == scale}):
                subset = [row for row in rows if row["scale"] == scale and row["condition"] == condition and row.get("ok") == "True"]
                for metric, unit in [
                    ("p50_ms", "ms"),
                    ("p95_ms", "ms"),
                    ("p99_ms", "ms"),
                    ("throughput_rps", "requests/s"),
                ]:
                    records.append({
                        "run_id": run_dir.name,
                        "comparison_group": scale,
                        "policy": condition,
                        "metric": metric,
                        "unit": unit,
                        "source_file": "raw/fortio_repetitions.csv",
                        **describe(numeric(row.get(metric)) for row in subset),
                    })

    gda = raw / "gda_overhead_repetitions.csv"
    if gda.exists():
        rows = read_csv_rows(gda)
        if rows and "mode" in rows[0]:
            for service_count in sorted({row["service_count"] for row in rows}, key=lambda item: int(float(item))):
                for mode in sorted({row["mode"] for row in rows if row["service_count"] == service_count}):
                    subset = [row for row in rows if row["service_count"] == service_count and row["mode"] == mode]
                    for metric, unit in [
                        ("graph_build_wall_ms", "ms"),
                        ("graph_build_cpu_ms", "ms"),
                        ("peak_python_memory_mib", "MiB"),
                        ("query_count", "count"),
                    ]:
                        records.append({
                            "run_id": run_dir.name,
                            "comparison_group": f"services{service_count}",
                            "policy": mode,
                            "metric": metric,
                            "unit": unit,
                            "source_file": "raw/gda_overhead_repetitions.csv",
                            **describe(numeric(row.get(metric)) for row in subset),
                        })

    by_key = {(row["comparison_group"], row["metric"], row["policy"]): row for row in records}
    baselines = {
        group_metric: sorted(policy for (group, metric, policy) in by_key if (group, metric) == group_metric and policy in {"kubernetes", "default", "no-sidecar", "dense-pairwise"})[:1]
        for group_metric in {(row["comparison_group"], row["metric"]) for row in records}
    }
    for row in records:
        baseline_policy = (baselines.get((row["comparison_group"], row["metric"])) or [None])[0]
        baseline = by_key.get((row["comparison_group"], row["metric"], baseline_policy)) if baseline_policy else None
        delta = deltas(row.get("mean"), baseline.get("mean") if baseline else None)
        row["baseline_policy"] = baseline_policy or ""
        row.update(delta)

    if records:
        out_json = run_dir / "processed" / "detailed_statistics.json"
        out_csv = run_dir / "processed" / "detailed_statistics.csv"
        out_json.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
        with out_csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    return records


def write_pivot_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    policies = sorted({row["policy"] for row in rows})
    by_key = {(row["policy"], row["metric"]): row for row in rows}
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "metric", "unit", *policies, "sources"])
        for metric in DISPLAY_METRICS:
            metric_rows = [by_key.get((policy, metric)) for policy in policies]
            unit = next((row["unit"] for row in metric_rows if row), "")
            sources = "; ".join(
                sorted({f"{row['policy']}:{row['source_file']}#{row['source_column']}" for row in metric_rows if row and row["source_file"]})
            )
            writer.writerow([path.parents[1].name, metric, unit, *[fmt(row["value"]) if row else "n/a" for row in metric_rows], sources])


def write_markdown(path: Path, run_id: str, rows: list[dict[str, Any]]) -> None:
    policies = sorted({row["policy"] for row in rows})
    by_key = {(row["policy"], row["metric"]): row for row in rows}
    lines = [
        f"# Standard Evaluation Summary: {run_id}",
        "",
        f"Source run ledger: `experiments/runs/{run_id}`",
        "",
        "| Metric | Unit | " + " | ".join(policies) + " | Source |",
        "| --- | --- | " + " | ".join("---:" for _ in policies) + " | --- |",
    ]
    for metric in DISPLAY_METRICS:
        metric_rows = [by_key.get((policy, metric)) for policy in policies]
        unit = next((row["unit"] for row in metric_rows if row), "")
        values = [fmt(row["value"]) if row else "n/a" for row in metric_rows]
        sources = "; ".join(
            sorted({f"`{row['source_file']}#{row['source_column']}`" for row in metric_rows if row and row["source_file"]})
        )
        lines.append(f"| `{metric}` | {unit} | " + " | ".join(values) + f" | {sources or 'not measured'} |")

    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    ledger = run_dir(args.run_id)
    metrics_path = ensure_standard_metrics(ledger, args.refresh)
    rows = load_metrics(metrics_path)
    processed = ledger / "processed"
    write_detailed_stats(ledger)
    write_pivot_csv(processed / "standard_summary_table.csv", rows)
    write_markdown(processed / "standard_summary_table.md", args.run_id, rows)
    print(processed / "standard_summary_table.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
