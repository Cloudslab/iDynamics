#!/usr/bin/env python3
"""Run network trace replay/generation and archive metrics in a run ledger."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from idynamics.network.traces import (
    BurstCorrelatedProvider,
    CsvMatrixReplayProvider,
    NetworkTraceFrame,
    SyntheticDistanceRandomProvider,
    compute_network_metrics,
    write_frames_csv,
    write_metrics_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--nodes", type=int, default=5)
    parser.add_argument("--steps", type=int, default=36)
    parser.add_argument("--interval-s", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=21)
    parser.add_argument("--csv-trace", default="")
    return parser.parse_args()


def materialize(provider) -> List[NetworkTraceFrame]:
    return list(provider.frames())


def write_metrics_csv(all_metrics: Dict[str, Dict[str, Dict[str, float]]], path: Path) -> None:
    metric_names = [
        "p50",
        "p95",
        "p99",
        "coefficient_of_variation",
        "peak_to_median",
        "lag1_autocorrelation",
        "spatial_correlation",
        "burst_duration_s",
        "recovery_time_s",
        "burst_count",
    ]
    with path.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["provider", "metric", *metric_names])
        for provider_name, provider_metrics in all_metrics.items():
            for metric, values in provider_metrics.items():
                writer.writerow([provider_name, metric, *[values[name] for name in metric_names]])



def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    raw = run_dir / "raw"
    processed = run_dir / "processed"
    figures = run_dir / "figures"
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    synthetic_provider = SyntheticDistanceRandomProvider(
        num_nodes=args.nodes, steps=args.steps, interval_s=args.interval_s, seed=args.seed
    )
    burst_provider = BurstCorrelatedProvider(
        num_nodes=args.nodes, steps=args.steps, interval_s=args.interval_s, seed=args.seed + 1
    )

    synthetic_frames = materialize(synthetic_provider)
    burst_frames = materialize(burst_provider)
    write_frames_csv(synthetic_frames, raw / "synthetic_distance_random_trace.csv")
    write_frames_csv(burst_frames, raw / "burst_correlated_trace.csv")

    csv_path = Path(args.csv_trace) if args.csv_trace else raw / "burst_correlated_trace.csv"
    csv_frames = materialize(CsvMatrixReplayProvider(csv_path, num_nodes=args.nodes))
    write_frames_csv(csv_frames, raw / "csv_replay_trace.csv")

    all_metrics = {
        "synthetic_distance_random": compute_network_metrics(synthetic_frames),
        "burst_correlated": compute_network_metrics(burst_frames),
        "csv_replay": compute_network_metrics(csv_frames),
    }
    write_metrics_json(all_metrics, processed / "network_trace_metrics.json")
    write_metrics_csv(all_metrics, processed / "network_trace_metrics.csv")

    (run_dir / "provider_metadata.json").write_text(
        json.dumps(
            {
                "synthetic_distance_random": synthetic_provider.metadata(),
                "burst_correlated": burst_provider.metadata(),
                "csv_replay": CsvMatrixReplayProvider(csv_path, num_nodes=args.nodes).metadata(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
