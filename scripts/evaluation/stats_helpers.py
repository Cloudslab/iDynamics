#!/usr/bin/env python3
"""Small dependency-free statistical helpers for experiment results summaries."""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Iterable
from typing import Any


def numeric(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def clean(values: Iterable[Any]) -> list[float]:
    return [value for value in (numeric(item) for item in values) if value is not None]


def percentile(values: Iterable[Any], pct: float) -> float | None:
    ordered = sorted(clean(values))
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def iqr(values: Iterable[Any]) -> float | None:
    q1 = percentile(values, 25)
    q3 = percentile(values, 75)
    if q1 is None or q3 is None:
        return None
    return q3 - q1


def sample_stddev(values: Iterable[Any]) -> float | None:
    vals = clean(values)
    if len(vals) < 2:
        return None
    return statistics.stdev(vals)


def mean(values: Iterable[Any]) -> float | None:
    vals = clean(values)
    return statistics.fmean(vals) if vals else None


def median(values: Iterable[Any]) -> float | None:
    vals = clean(values)
    return statistics.median(vals) if vals else None


def bootstrap_ci_mean(
    values: Iterable[Any],
    *,
    confidence: float = 0.95,
    samples: int = 2000,
    seed: int = 13,
) -> tuple[float | None, float | None]:
    vals = clean(values)
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], vals[0]
    rng = random.Random(seed)
    boot = []
    for _ in range(samples):
        draw = [vals[rng.randrange(len(vals))] for _ in vals]
        boot.append(statistics.fmean(draw))
    alpha = (1.0 - confidence) / 2.0
    return percentile(boot, alpha * 100.0), percentile(boot, (1.0 - alpha) * 100.0)


def describe(values: Iterable[Any]) -> dict[str, float | int | None]:
    vals = clean(values)
    ci_low, ci_high = bootstrap_ci_mean(vals)
    return {
        "n": len(vals),
        "mean": mean(vals),
        "median": median(vals),
        "p95": percentile(vals, 95),
        "p99": percentile(vals, 99),
        "stddev": sample_stddev(vals),
        "iqr": iqr(vals),
        "mean_ci95_low": ci_low,
        "mean_ci95_high": ci_high,
    }


def deltas(candidate: float | None, baseline: float | None) -> dict[str, float | None]:
    if candidate is None or baseline is None:
        return {"absolute_delta": None, "percentage_delta": None}
    pct = None if baseline == 0 else ((candidate - baseline) / baseline) * 100.0
    return {"absolute_delta": candidate - baseline, "percentage_delta": pct}
