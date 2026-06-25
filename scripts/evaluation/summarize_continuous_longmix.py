#!/usr/bin/env python3
"""Summarize continuous long-mix run ledgers."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Path to experiments/runs/<run_id>.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as input_file:
        return list(csv.DictReader(input_file))


def write_csv(path: Path, fieldnames: list[str], rows: list[Mapping[str, object]]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_policy_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    policies = sorted({row["policy"] for row in rows})
    summary = []
    for policy in policies:
        subset = [row for row in rows if row["policy"] == policy]
        summary.append(
            {
                "policy": policy,
                "policy_display_name": subset[0].get("policy_display_name", policy),
                "evidence_type": subset[0].get("evidence_type", "replay/model/control-plane"),
                "steps": len(subset),
                "mean_latency_ms": f"{statistics.fmean(float(row['latency_ms']) for row in subset):.6f}",
                "mean_sla_violation_ratio": f"{statistics.fmean(float(row['sla_violation_ratio']) for row in subset):.6f}",
                "max_sla_violation_ratio": f"{max(float(row['sla_violation_ratio']) for row in subset):.6f}",
                "mean_request_mix_entropy": f"{statistics.fmean(float(row.get('request_mix_entropy', 0.0)) for row in subset):.6f}",
                "mean_active_edge_count": f"{statistics.fmean(float(row.get('active_edge_count', 0.0)) for row in subset):.6f}",
                "migration_count_available": any(row.get("migration_count") for row in subset),
                "policy_decision_time_available": any(row.get("policy_decision_time_ms") for row in subset),
            }
        )
    return summary


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    raw_dir = run_dir / "raw"
    processed_dir = run_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    mix_rows = read_csv(raw_dir / "request_mix_timeseries.csv")
    policy_path = raw_dir / "e2e_policy_timeseries.csv"
    if not policy_path.exists():
        policy_path = raw_dir / "policy_replay_timeseries.csv"
    policy_rows = read_csv(policy_path)

    metrics = {
        "steps": len(mix_rows),
        "mean_request_mix_entropy": statistics.fmean(float(row["request_mix_entropy"]) for row in mix_rows),
        "mean_top3_hotspot_churn": statistics.fmean(float(row["top3_hotspot_churn"]) for row in mix_rows[1:]) if len(mix_rows) > 1 else 0.0,
        "mean_active_edge_count": statistics.fmean(float(row["active_edge_count"]) for row in mix_rows),
        "mean_traffic_stress_gini": statistics.fmean(float(row["traffic_stress_gini"]) for row in mix_rows),
        "mean_traffic_stress_skew": statistics.fmean(float(row["traffic_stress_skew"]) for row in mix_rows),
        "policy_latency_evidence_type": "replay/model/control-plane",
    }
    (processed_dir / "continuous_graph_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")

    summary_rows = summarize_policy_rows(policy_rows)
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
        summary_rows,
    )
    (processed_dir / "mode_summary.md").write_text(
        "\n".join(
            [
                "# Continuous Long-Mix Summary",
                "",
                f"Run: `{run_dir.name}`",
                f"Steps: `{len(mix_rows)}`",
                "Policy latency/SLA evidence type: `replay/model/control-plane` unless live e2e rows are supplied.",
                f"Mean request-mix entropy: {metrics['mean_request_mix_entropy']:.4f}",
                f"Mean top-3 hotspot churn: {metrics['mean_top3_hotspot_churn']:.4f}",
                f"Mean active edge count: {metrics['mean_active_edge_count']:.2f}",
                "",
            ]
        )
    )
    print(processed_dir / "policy_e2e_summary.csv")
    print(processed_dir / "continuous_graph_metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
