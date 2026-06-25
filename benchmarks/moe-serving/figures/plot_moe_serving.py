#!/usr/bin/env python3
"""Plot MoE policy latency from a physical run evaluation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    app_timeseries = args.run_dir / "processed" / "application_policy_timeseries.csv"
    if not app_timeseries.exists():
        app_timeseries = args.run_dir / "raw" / "application_policy_timeseries.csv"
    if app_timeseries.exists():
        with app_timeseries.open(newline="") as input_file:
            rows = list(csv.DictReader(input_file))
        grouped: dict[str, list[float]] = {}
        for row in rows:
            grouped.setdefault(row["policy"], []).append(float(row["latency_ms"]))
        metrics = {
            policy: {
                "p50_latency_ms": sorted(values)[len(values) // 2],
                "p95_latency_ms": sorted(values)[min(len(values) - 1, int(0.95 * (len(values) - 1)))],
            }
            for policy, values in grouped.items()
            if values
        }
    else:
        source = args.run_dir / "processed" / "policy_metrics.json"
        if not source.exists():
            source = args.run_dir / "processed" / "summary.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        metrics = data.get("policies", data)
    rows = [(name, item) for name, item in metrics.items() if isinstance(item, dict) and "p95_latency_ms" in item]
    if not rows:
        raise SystemExit(f"no policy latency metrics found in {source}")

    import matplotlib.pyplot as plt

    labels = [name.replace("policy", "p") for name, _ in rows]
    p50 = [float(item.get("p50_latency_ms", 0.0)) for _, item in rows]
    p95 = [float(item.get("p95_latency_ms", 0.0)) for _, item in rows]
    output = args.output or args.run_dir / "figures" / "moe_serving_latency.svg"
    output.parent.mkdir(parents=True, exist_ok=True)

    x = range(len(labels))
    plt.figure(figsize=(6.4, 3.4))
    plt.bar([v - 0.18 for v in x], p50, width=0.36, label="p50")
    plt.bar([v + 0.18 for v in x], p95, width=0.36, label="p95")
    plt.xticks(list(x), labels, rotation=20, ha="right")
    plt.ylabel("Latency (ms)")
    plt.title("MoE Serving Policy Latency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
