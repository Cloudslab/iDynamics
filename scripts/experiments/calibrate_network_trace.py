#!/usr/bin/env python3
"""Calibrate burst-correlated network dynamics against a small RIPE Atlas sample."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from idynamics.network.traces import (
    BurstCorrelatedProvider,
    coefficient_of_variation,
    compute_network_metrics,
    lag1_autocorrelation,
    pearson_correlation,
    percentile,
    write_frames_csv,
)


RIPE_ATLAS_TERMS_URL = "https://www.ripe.net/about-us/legal/ripe-atlas-service-terms-and-conditions/"
RIPE_ATLAS_RESULTS_DOC_URL = (
    "https://beta-ui.atlas.ripe.net/docs/apis/rest-api-reference/measurements/measurements_results"
)
RIPE_ATLAS_BUILTIN_DOC_URL = "https://ui.prod.atlas.ripe.net/docs/getting-started/built-in-measurements"


@dataclass(frozen=True)
class AtlasPingPoint:
    probe_id: int
    timestamp: int
    rtt_ms: float


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_root() -> Path:
    try:
        output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        return Path(output)
    except Exception:
        return Path.cwd()


def run_capture(command: Sequence[str], cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return completed.stdout + completed.stderr


def init_ledger(root: Path, run_id: str, config: Mapping[str, object]) -> Path:
    run_dir = root / "experiments" / "runs" / run_id
    for child in ("env", "raw", "processed", "figures", "logs"):
        (run_dir / child).mkdir(parents=True, exist_ok=True)
    write_yaml(config, run_dir / "config.yaml")
    (run_dir / "git_sha.txt").write_text(run_capture(["git", "rev-parse", "HEAD"], root).strip() + "\n")
    (run_dir / "git_status.txt").write_text(run_capture(["git", "status", "--short", "--branch"], root))
    (run_dir / "codex_model.txt").write_text("codex-cli-local\n")
    (run_dir / "commands.log").write_text("")
    (run_dir / "env" / "host_metadata.txt").write_text(
        run_capture(["bash", "-lc", "hostname; date -u +%Y-%m-%dT%H:%M:%SZ; uname -a"], root)
    )
    return run_dir


def write_yaml(data: Mapping[str, object], path: Path) -> None:
    lines: List[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, str):
            lines.append(f"{key}: {json.dumps(value)}")
        else:
            lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n")


def log_command(run_dir: Path, command: str) -> None:
    with (run_dir / "commands.log").open("a") as handle:
        handle.write(f"[{datetime.now(timezone.utc).isoformat()}] {command}\n")


def fetch_json(url: str, timeout_s: int) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": "iDynamics-trace-calibration/1.0"})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return json.load(response)


def fetch_probe_ids(page_size: int, timeout_s: int) -> List[int]:
    params = urllib.parse.urlencode({"status": 1, "af": 4, "page_size": page_size, "format": "json"})
    data = fetch_json(f"https://atlas.ripe.net/api/v2/probes/?{params}", timeout_s)
    if not isinstance(data, dict):
        raise RuntimeError("unexpected RIPE Atlas probes response")
    return [int(probe["id"]) for probe in data.get("results", [])]


def fetch_atlas_results(
    measurement_id: int,
    probe_ids: Sequence[int],
    start_ts: int,
    stop_ts: int,
    timeout_s: int,
) -> List[Mapping[str, object]]:
    params = urllib.parse.urlencode(
        {
            "start": start_ts,
            "stop": stop_ts,
            "format": "json",
            "public_only": "true",
            "probe_ids": ",".join(str(probe_id) for probe_id in probe_ids),
        }
    )
    url = f"https://atlas.ripe.net/api/v2/measurements/{measurement_id}/results/?{params}"
    data = fetch_json(url, timeout_s)
    if not isinstance(data, list):
        raise RuntimeError("unexpected RIPE Atlas measurement results response")
    return data


def parse_ping_points(rows: Iterable[Mapping[str, object]]) -> List[AtlasPingPoint]:
    points: List[AtlasPingPoint] = []
    for row in rows:
        if row.get("type") != "ping" or "avg" not in row:
            continue
        try:
            rtt_ms = float(row["avg"])
            if not math.isfinite(rtt_ms):
                continue
            points.append(AtlasPingPoint(int(row["prb_id"]), int(row["timestamp"]), rtt_ms))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(points, key=lambda point: (point.probe_id, point.timestamp))


def write_points_csv(points: Sequence[AtlasPingPoint], path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["probe_id", "timestamp", "rtt_ms"])
        for point in points:
            writer.writerow([point.probe_id, point.timestamp, point.rtt_ms])


def external_latency_metrics(points: Sequence[AtlasPingPoint], bin_s: int) -> Dict[str, float]:
    values = [point.rtt_ms for point in points]
    by_probe: Dict[int, List[AtlasPingPoint]] = defaultdict(list)
    for point in points:
        by_probe[point.probe_id].append(point)
    lag_values = [
        lag1_autocorrelation([point.rtt_ms for point in sorted(series, key=lambda item: item.timestamp)])
        for series in by_probe.values()
        if len(series) > 2
    ]
    spatial_values = spatial_probe_correlations(points, bin_s)
    med = percentile(values, 50)
    return {
        "p50": med,
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "coefficient_of_variation": coefficient_of_variation(values),
        "peak_to_median": max(values) / med if med else 0.0,
        "lag1_autocorrelation": mean(lag_values) if lag_values else 0.0,
        "spatial_correlation": mean(spatial_values) if spatial_values else 0.0,
        "probe_count": float(len(by_probe)),
        "sample_count": float(len(points)),
    }


def spatial_probe_correlations(points: Sequence[AtlasPingPoint], bin_s: int) -> List[float]:
    by_probe_bin: Dict[int, Dict[int, float]] = defaultdict(dict)
    for point in points:
        by_probe_bin[point.probe_id][point.timestamp // bin_s] = point.rtt_ms
    probes = sorted(by_probe_bin)
    correlations: List[float] = []
    for idx, probe_a in enumerate(probes):
        for probe_b in probes[idx + 1 :]:
            common_bins = sorted(set(by_probe_bin[probe_a]) & set(by_probe_bin[probe_b]))
            if len(common_bins) < 3:
                continue
            correlations.append(
                pearson_correlation(
                    [by_probe_bin[probe_a][bin_id] for bin_id in common_bins],
                    [by_probe_bin[probe_b][bin_id] for bin_id in common_bins],
                )
            )
    return correlations


def metric_distance(external: Mapping[str, float], synthetic: Mapping[str, float]) -> float:
    keys = [
        "p50",
        "p95",
        "p99",
        "coefficient_of_variation",
        "peak_to_median",
        "lag1_autocorrelation",
        "spatial_correlation",
    ]
    total = 0.0
    for key in keys:
        scale = max(abs(external[key]), 1.0)
        total += ((synthetic[key] - external[key]) / scale) ** 2
    return math.sqrt(total / len(keys))


def fit_burst_provider(
    external: Mapping[str, float],
    num_nodes: int,
    steps: int,
    interval_s: float,
    seed: int,
) -> Tuple[Dict[str, object], Dict[str, float], List[Dict[str, object]]]:
    candidates: List[Dict[str, object]] = []
    best_params: Dict[str, object] | None = None
    best_metrics: Dict[str, float] | None = None
    best_score = float("inf")
    base_latency = max(1.0, float(external["p50"]) * 0.65)
    for temporal in (0.35, 0.55, 0.75, 0.90, 0.97):
        for spatial in (0.0, 0.25, 0.50, 0.75):
            for burst_probability in (0.0, 0.02, 0.05, 0.08, 0.12):
                provider = BurstCorrelatedProvider(
                    num_nodes=num_nodes,
                    steps=steps,
                    interval_s=interval_s,
                    base_latency_ms=base_latency,
                    temporal_correlation=temporal,
                    spatial_correlation=spatial,
                    burst_probability=burst_probability,
                    burst_latency_multiplier=(1.2, 3.5),
                    seed=seed,
                )
                frames = list(provider.frames())
                latency_metrics = compute_network_metrics(frames)["latency_ms"]
                score = metric_distance(external, latency_metrics)
                params = dict(provider.metadata())
                row = {"score": score, "params": params, "latency_metrics": latency_metrics}
                candidates.append(row)
                if score < best_score:
                    best_score = score
                    best_params = params
                    best_metrics = latency_metrics
    assert best_params is not None and best_metrics is not None
    return best_params, best_metrics, sorted(candidates, key=lambda row: float(row["score"]))[:10]


def write_metrics_csv(metrics: Mapping[str, Mapping[str, float]], path: Path) -> None:
    keys = [
        "p50",
        "p95",
        "p99",
        "coefficient_of_variation",
        "peak_to_median",
        "lag1_autocorrelation",
        "spatial_correlation",
        "probe_count",
        "sample_count",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", *keys])
        for source, values in metrics.items():
            writer.writerow([source, *[values.get(key, "") for key in keys]])


def write_summary(
    run_dir: Path,
    measurement_id: int,
    source_window: Tuple[int, int],
    requested_probe_ids: Sequence[int],
    contributing_probe_ids: Sequence[int],
    external: Mapping[str, float],
    fitted: Mapping[str, float],
    best_params: Mapping[str, object],
) -> None:
    start_iso = datetime.fromtimestamp(source_window[0], timezone.utc).isoformat()
    stop_iso = datetime.fromtimestamp(source_window[1], timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=f"network-trace-calibrated-{utc_stamp()}")
    parser.add_argument("--measurement-id", type=int, default=1001)
    parser.add_argument("--probe-count", type=int, default=12)
    parser.add_argument("--window-hours", type=float, default=24.0)
    parser.add_argument("--timeout-s", type=int, default=60)
    parser.add_argument("--seed", type=int, default=46)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    stop_ts = int(time.time()) - 3600
    start_ts = stop_ts - int(args.window_hours * 3600)
    config = {
        "run_id": args.run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "external latency trace calibration",
        "physical_scale_claim": "none",
        "source": "RIPE Atlas built-in public ping results",
        "measurement_id": args.measurement_id,
        "window_hours": args.window_hours,
        "probe_count_requested": args.probe_count,
        "tc_mutation": "none",
    }
    run_dir = init_ledger(root, args.run_id, config)
    try:
        probe_ids = fetch_probe_ids(args.probe_count, args.timeout_s)
        if len(probe_ids) < 3:
            raise RuntimeError("fewer than three connected RIPE Atlas IPv4 probes returned")
        log_command(run_dir, f"fetch RIPE Atlas probes status=1 af=4 page_size={args.probe_count}")
        rows = fetch_atlas_results(args.measurement_id, probe_ids, start_ts, stop_ts, args.timeout_s)
        log_command(
            run_dir,
            "fetch RIPE Atlas measurement results "
            f"measurement_id={args.measurement_id} start={start_ts} stop={stop_ts} probes={','.join(map(str, probe_ids))}",
        )
        points = parse_ping_points(rows)
        if len(points) < args.probe_count * 3:
            raise RuntimeError(f"insufficient RIPE Atlas ping points parsed: {len(points)}")
        (run_dir / "raw" / "ripe_atlas_results.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
        write_points_csv(points, run_dir / "raw" / "ripe_atlas_ping_rtt.csv")
        step_values = [int(row.get("step", 240)) for row in rows if isinstance(row.get("step"), int)]
        bin_s = int(median(step_values)) if step_values else 240
        external = external_latency_metrics(points, bin_s)
        by_probe = defaultdict(list)
        for point in points:
            by_probe[point.probe_id].append(point)
        steps = max(len(series) for series in by_probe.values())
        interval_s = float(bin_s)
        best_params, fitted, top_candidates = fit_burst_provider(
            external, num_nodes=len(by_probe), steps=steps, interval_s=interval_s, seed=args.seed
        )
        fitted_provider = BurstCorrelatedProvider(
            num_nodes=len(by_probe),
            steps=steps,
            interval_s=interval_s,
            base_latency_ms=float(best_params["base_latency_ms"]),
            temporal_correlation=float(best_params["temporal_correlation"]),
            spatial_correlation=float(best_params["spatial_correlation"]),
            burst_probability=float(best_params["burst_probability"]),
            burst_latency_multiplier=tuple(best_params["burst_latency_multiplier"]),  # type: ignore[arg-type]
            seed=args.seed,
        )
        fitted_frames = list(fitted_provider.frames())
        write_frames_csv(fitted_frames, run_dir / "raw" / "fitted_burst_correlated_trace.csv")
        processed = {
            "ripe_atlas": external,
            "fitted_burst_correlated": fitted,
            "fit_score": {"latency_metric_distance": metric_distance(external, fitted)},
        }
        (run_dir / "processed" / "calibration_metrics.json").write_text(
            json.dumps(processed, indent=2, sort_keys=True) + "\n"
        )
        write_metrics_csv({"ripe_atlas": external, "fitted_burst_correlated": fitted}, run_dir / "processed" / "calibration_metrics.csv")
        (run_dir / "processed" / "fit_candidates.json").write_text(
            json.dumps(top_candidates, indent=2, sort_keys=True) + "\n"
        )
        (run_dir / "provider_metadata.json").write_text(
            json.dumps({"selected": best_params, "source_probe_ids": probe_ids}, indent=2, sort_keys=True) + "\n"
        )

        contributing_probe_ids = sorted(by_probe)
        write_summary(
            run_dir,
            args.measurement_id,
            (start_ts, stop_ts),
            probe_ids,
            contributing_probe_ids,
            external,
            fitted,
            best_params,
        )
    except Exception as exc:
        (run_dir / "summary.md").write_text(
            f"""# {run_dir.name}

Status: blocked

## Purpose
Calibrate burst-correlated network dynamics against a public RIPE Atlas sample.

## Result
Calibration failed before producing a usable external sample: `{exc}`.

"""
        )
        print(f"calibration failed: {exc}", file=sys.stderr)
        return 1
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
