"""Network trace providers and dynamics metrics for iDynamics experiments.

The providers in this module intentionally separate trace generation/replay from
traffic-control mutation.  Experiment scripts can compute and archive the exact
time-indexed latency/bandwidth matrices first, then decide whether to apply a
frame to a live cluster under the repository's qdisc snapshot/reset guardrails.
"""

from __future__ import annotations

import csv
import json
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


Matrix = List[List[float]]


@dataclass(frozen=True)
class NetworkTraceFrame:
    """One time-indexed network state."""

    time_s: float
    latency_ms: Matrix
    bandwidth_mbps: Matrix


class NetworkTraceProvider(ABC):
    """Interface for latency/bandwidth matrix providers."""

    @abstractmethod
    def frames(self) -> Iterable[NetworkTraceFrame]:
        """Yield network trace frames in nondecreasing time order."""

    @abstractmethod
    def metadata(self) -> Mapping[str, object]:
        """Return provider configuration suitable for run-ledger archival."""


def _zero_diagonal(matrix: Matrix) -> Matrix:
    return [[0.0 if i == j else float(value) for j, value in enumerate(row)] for i, row in enumerate(matrix)]


def _new_matrix(size: int, value: float = 0.0) -> Matrix:
    return [[float(value) for _ in range(size)] for _ in range(size)]


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class SyntheticDistanceRandomProvider(NetworkTraceProvider):
    """Baseline provider compatible with the original distance-random matrices."""

    def __init__(
        self,
        num_nodes: int,
        steps: int = 12,
        interval_s: float = 5.0,
        base_latency_ms: float = 5.0,
        max_additional_latency_ms: float = 50.0,
        min_bandwidth_mbps: float = 200.0,
        max_bandwidth_mbps: float = 800.0,
        seed: int = 7,
    ) -> None:
        self.num_nodes = num_nodes
        self.steps = steps
        self.interval_s = interval_s
        self.base_latency_ms = base_latency_ms
        self.max_additional_latency_ms = max_additional_latency_ms
        self.min_bandwidth_mbps = min_bandwidth_mbps
        self.max_bandwidth_mbps = max_bandwidth_mbps
        self.seed = seed

    def frames(self) -> Iterable[NetworkTraceFrame]:
        rng = random.Random(self.seed)
        for step in range(self.steps):
            latency = _new_matrix(self.num_nodes)
            bandwidth = _new_matrix(self.num_nodes)
            for i in range(self.num_nodes):
                for j in range(self.num_nodes):
                    if i == j:
                        continue
                    distance_factor = abs(i - j) / max(1, self.num_nodes - 1)
                    congestion_factor = rng.uniform(0.5, 1.5)
                    latency[i][j] = (
                        self.base_latency_ms
                        + rng.uniform(0.0, self.max_additional_latency_ms) * distance_factor
                    ) * congestion_factor
                    bandwidth[i][j] = rng.uniform(self.min_bandwidth_mbps, self.max_bandwidth_mbps)
            yield NetworkTraceFrame(step * self.interval_s, _zero_diagonal(latency), _zero_diagonal(bandwidth))

    def metadata(self) -> Mapping[str, object]:
        return {
            "provider": "SyntheticDistanceRandomProvider",
            "num_nodes": self.num_nodes,
            "steps": self.steps,
            "interval_s": self.interval_s,
            "base_latency_ms": self.base_latency_ms,
            "max_additional_latency_ms": self.max_additional_latency_ms,
            "min_bandwidth_mbps": self.min_bandwidth_mbps,
            "max_bandwidth_mbps": self.max_bandwidth_mbps,
            "seed": self.seed,
        }


class CsvMatrixReplayProvider(NetworkTraceProvider):
    """Replay time-indexed NxN latency and bandwidth matrices from CSV.

    Supported CSV formats:
    - long: ``time_s,metric,src,dst,value`` where metric is latency_ms or
      bandwidth_mbps.
    - pair-long: ``time_s,src,dst,latency_ms,bandwidth_mbps``.
    """

    def __init__(self, path: str | Path, num_nodes: Optional[int] = None) -> None:
        self.path = Path(path)
        self.num_nodes = num_nodes
        if not self.path.exists():
            raise FileNotFoundError(self.path)

    def frames(self) -> Iterable[NetworkTraceFrame]:
        rows = list(csv.DictReader(self.path.open(newline="")))
        if not rows:
            return
        max_index = -1
        for row in rows:
            max_index = max(max_index, int(row["src"]), int(row["dst"]))
        size = self.num_nodes or max_index + 1
        grouped: Dict[float, Tuple[Matrix, Matrix]] = {}
        for row in rows:
            t = float(row["time_s"])
            latency, bandwidth = grouped.setdefault(t, (_new_matrix(size), _new_matrix(size)))
            src = int(row["src"])
            dst = int(row["dst"])
            if "metric" in row and row["metric"]:
                metric = row["metric"].strip()
                if metric == "latency_ms":
                    latency[src][dst] = float(row["value"])
                elif metric == "bandwidth_mbps":
                    bandwidth[src][dst] = float(row["value"])
                else:
                    raise ValueError(f"unsupported metric in {self.path}: {metric}")
            else:
                latency[src][dst] = float(row["latency_ms"])
                bandwidth[src][dst] = float(row["bandwidth_mbps"])
        for t in sorted(grouped):
            latency, bandwidth = grouped[t]
            yield NetworkTraceFrame(t, _zero_diagonal(latency), _zero_diagonal(bandwidth))

    def metadata(self) -> Mapping[str, object]:
        return {"provider": "CsvMatrixReplayProvider", "path": str(self.path), "num_nodes": self.num_nodes}


class BurstCorrelatedProvider(NetworkTraceProvider):
    """Generate bursty traces with temporal and spatial correlation."""

    def __init__(
        self,
        num_nodes: int,
        steps: int = 36,
        interval_s: float = 5.0,
        base_latency_ms: float = 8.0,
        base_bandwidth_mbps: float = 650.0,
        temporal_correlation: float = 0.82,
        spatial_correlation: float = 0.65,
        burst_probability: float = 0.08,
        burst_duration_steps: Tuple[int, int] = (3, 8),
        burst_latency_multiplier: Tuple[float, float] = (2.0, 6.0),
        burst_bandwidth_multiplier: Tuple[float, float] = (0.20, 0.70),
        jitter_fraction: float = 0.12,
        seed: int = 11,
    ) -> None:
        self.num_nodes = num_nodes
        self.steps = steps
        self.interval_s = interval_s
        self.base_latency_ms = base_latency_ms
        self.base_bandwidth_mbps = base_bandwidth_mbps
        self.temporal_correlation = temporal_correlation
        self.spatial_correlation = spatial_correlation
        self.burst_probability = burst_probability
        self.burst_duration_steps = burst_duration_steps
        self.burst_latency_multiplier = burst_latency_multiplier
        self.burst_bandwidth_multiplier = burst_bandwidth_multiplier
        self.jitter_fraction = jitter_fraction
        self.seed = seed

    def frames(self) -> Iterable[NetworkTraceFrame]:
        rng = random.Random(self.seed)
        latent = _new_matrix(self.num_nodes)
        active_bursts: Dict[Tuple[int, int], Tuple[int, float, float]] = {}
        previous_latency = _new_matrix(self.num_nodes, self.base_latency_ms)
        previous_bandwidth = _new_matrix(self.num_nodes, self.base_bandwidth_mbps)

        for step in range(self.steps):
            shared_noise = rng.gauss(0.0, 1.0)
            latency = _new_matrix(self.num_nodes)
            bandwidth = _new_matrix(self.num_nodes)
            for i in range(self.num_nodes):
                for j in range(self.num_nodes):
                    if i == j:
                        continue
                    pair = (i, j)
                    pair_noise = rng.gauss(0.0, 1.0)
                    
                    '''
                    spatial_correlation close to 0: each pair behaves mostly independently
                    spatial_correlation close to 1: many pairs move together due to shared bottleneck/noise
                    '''
                    latent[i][j] = (
                        self.spatial_correlation * shared_noise
                        + (1.0 - self.spatial_correlation) * pair_noise
                    )
                    distance_factor = 1.0 + abs(i - j) / max(1, self.num_nodes - 1)
                    target_latency = self.base_latency_ms * distance_factor * (
                        1.0 + self.jitter_fraction * latent[i][j]
                    )
                    target_bandwidth = self.base_bandwidth_mbps / distance_factor * (
                        1.0 - self.jitter_fraction * latent[i][j]
                    )
                    if pair not in active_bursts and rng.random() < self.burst_probability:
                        duration = rng.randint(*self.burst_duration_steps)
                        active_bursts[pair] = (
                            step + duration,
                            rng.uniform(*self.burst_latency_multiplier),
                            rng.uniform(*self.burst_bandwidth_multiplier),
                        )
                    burst = active_bursts.get(pair)
                    if burst is not None:
                        end_step, latency_mult, bandwidth_mult = burst
                        if step <= end_step:
                            target_latency *= latency_mult
                            target_bandwidth *= bandwidth_mult
                        else:
                            del active_bursts[pair]
                    alpha = self.temporal_correlation
                    '''
                    temporal_correlation close to 0:  current frame follows the new target quickly
                    temporal_correlation close to 1:  current frame changes slowly, so bursts persist over time
                    '''
                    latency[i][j] = _clip(alpha * previous_latency[i][j] + (1 - alpha) * target_latency, 0.1, 10000)
                    bandwidth[i][j] = _clip(
                        alpha * previous_bandwidth[i][j] + (1 - alpha) * target_bandwidth, 1.0, 100000
                    )
            previous_latency = latency
            previous_bandwidth = bandwidth
            yield NetworkTraceFrame(step * self.interval_s, _zero_diagonal(latency), _zero_diagonal(bandwidth))

    def metadata(self) -> Mapping[str, object]:
        return {
            "provider": "BurstCorrelatedProvider",
            "num_nodes": self.num_nodes,
            "steps": self.steps,
            "interval_s": self.interval_s,
            "base_latency_ms": self.base_latency_ms,
            "base_bandwidth_mbps": self.base_bandwidth_mbps,
            "temporal_correlation": self.temporal_correlation,
            "spatial_correlation": self.spatial_correlation,
            "burst_probability": self.burst_probability,
            "burst_duration_steps": list(self.burst_duration_steps),
            "burst_latency_multiplier": list(self.burst_latency_multiplier),
            "burst_bandwidth_multiplier": list(self.burst_bandwidth_multiplier),
            "jitter_fraction": self.jitter_fraction,
            "seed": self.seed,
        }


def flatten_off_diagonal(frames: Sequence[NetworkTraceFrame], metric: str) -> List[float]:
    values: List[float] = []
    for frame in frames:
        matrix = frame.latency_ms if metric == "latency_ms" else frame.bandwidth_mbps
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                if i != j:
                    values.append(float(value))
    return values


def percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct / 100.0
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[int(rank)]
    return ordered[low] * (high - rank) + ordered[high] * (rank - low)


def coefficient_of_variation(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    if avg == 0:
        return 0.0
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / avg


def lag1_autocorrelation(series: Sequence[float]) -> float:
    if len(series) < 3:
        return 0.0
    x = series[:-1]
    y = series[1:]
    return pearson_correlation(x, y)


def pearson_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    mx = mean(x)
    my = mean(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0 or dy == 0:
        return 0.0
    return numerator / (dx * dy)


def _pair_series(frames: Sequence[NetworkTraceFrame], metric: str) -> Dict[Tuple[int, int], List[float]]:
    result: Dict[Tuple[int, int], List[float]] = {}
    for frame in frames:
        matrix = frame.latency_ms if metric == "latency_ms" else frame.bandwidth_mbps
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                if i != j:
                    result.setdefault((i, j), []).append(float(value))
    return result


def temporal_autocorrelation(frames: Sequence[NetworkTraceFrame], metric: str) -> float:
    values = [lag1_autocorrelation(series) for series in _pair_series(frames, metric).values() if len(series) > 2]
    return mean(values) if values else 0.0


def spatial_correlation(frames: Sequence[NetworkTraceFrame], metric: str) -> float:
    pair_values = _pair_series(frames, metric)
    pairs = sorted(pair_values)
    correlations: List[float] = []
    for idx, pair_a in enumerate(pairs):
        for pair_b in pairs[idx + 1 :]:
            if pair_a[0] == pair_b[0] or pair_a[1] == pair_b[1]:
                corr = pearson_correlation(pair_values[pair_a], pair_values[pair_b])
                correlations.append(corr)
    return mean(correlations) if correlations else 0.0


def burst_and_recovery_metrics(
    frames: Sequence[NetworkTraceFrame],
    metric: str,
    burst_threshold_multiplier: float = 1.5,
    recovery_tolerance: float = 0.10,
) -> Dict[str, float]:
    durations: List[float] = []
    recoveries: List[float] = []
    if len(frames) < 2:
        return {"burst_duration_s": 0.0, "recovery_time_s": 0.0, "burst_count": 0.0}
    interval = median([frames[i].time_s - frames[i - 1].time_s for i in range(1, len(frames))])
    for series in _pair_series(frames, metric).values():
        baseline = median(series)
        threshold = baseline * burst_threshold_multiplier
        index = 0
        while index < len(series):
            if series[index] <= threshold:
                index += 1
                continue
            start = index
            while index < len(series) and series[index] > threshold:
                index += 1
            durations.append((index - start) * interval)
            recovery_start = index
            recovery_threshold = baseline * (1.0 + recovery_tolerance)
            while index < len(series) and series[index] > recovery_threshold:
                index += 1
            recoveries.append(max(0, index - recovery_start) * interval)
    return {
        "burst_duration_s": mean(durations) if durations else 0.0,
        "recovery_time_s": mean(recoveries) if recoveries else 0.0,
        "burst_count": float(len(durations)),
    }


def compute_network_metrics(frames: Sequence[NetworkTraceFrame]) -> Dict[str, Dict[str, float]]:
    """Compute network dynamics summary metrics."""

    metrics: Dict[str, Dict[str, float]] = {}
    for metric_name in ("latency_ms", "bandwidth_mbps"):
        values = flatten_off_diagonal(frames, metric_name)
        med = percentile(values, 50)
        burst_metrics = burst_and_recovery_metrics(frames, metric_name)
        metrics[metric_name] = {
            "p50": med,
            "p95": percentile(values, 95),
            "p99": percentile(values, 99),
            "coefficient_of_variation": coefficient_of_variation(values),
            "peak_to_median": max(values) / med if values and med else 0.0,
            "lag1_autocorrelation": temporal_autocorrelation(frames, metric_name),
            "spatial_correlation": spatial_correlation(frames, metric_name),
            **burst_metrics,
        }
    return metrics


def write_frames_csv(frames: Sequence[NetworkTraceFrame], path: str | Path) -> None:
    with Path(path).open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["time_s", "src", "dst", "latency_ms", "bandwidth_mbps"])
        for frame in frames:
            for i in range(len(frame.latency_ms)):
                for j in range(len(frame.latency_ms)):
                    if i == j:
                        continue
                    writer.writerow([frame.time_s, i, j, frame.latency_ms[i][j], frame.bandwidth_mbps[i][j]])


def write_metrics_json(metrics: Mapping[str, Mapping[str, float]], path: str | Path) -> None:
    Path(path).write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
