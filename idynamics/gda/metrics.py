"""Pure service-graph dynamics metrics."""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping


EdgeWeights = Mapping[tuple[str, str], float]


def edge_jaccard_distance(previous: EdgeWeights, current: EdgeWeights) -> float:
    previous_edges = set(previous)
    current_edges = set(current)
    union = previous_edges | current_edges
    if not union:
        return 0.0
    return 1.0 - (len(previous_edges & current_edges) / len(union))


def weighted_edge_distance(previous: EdgeWeights, current: EdgeWeights) -> float:
    edges = set(previous) | set(current)
    numerator = sum(abs(previous.get(edge, 0.0) - current.get(edge, 0.0)) for edge in edges)
    denominator = sum(max(previous.get(edge, 0.0), current.get(edge, 0.0)) for edge in edges)
    return numerator / denominator if denominator > 0 else 0.0


def active_edge_count(edges: EdgeWeights, threshold: float = 0.0) -> int:
    """Count directed edges whose nonnegative weight exceeds a threshold."""

    return sum(1 for weight in edges.values() if max(0.0, weight) > threshold)


def traffic_stress(edges: EdgeWeights) -> float:
    """Aggregate weighted stress over active directed edges."""

    return sum(max(0.0, weight) for weight in edges.values())


def request_mix_entropy(probabilities: Mapping[str, float]) -> float:
    """Shannon entropy, in bits, for a request-type probability vector."""

    return -sum(value * math.log2(value) for value in probabilities.values() if value > 0.0)


def gini(values: Iterable[float]) -> float:
    value_list = list(values)
    if not value_list:
        return 0.0
    ordered = sorted(max(0.0, value) for value in value_list)
    total = sum(ordered)
    if total <= 0.0:
        return 0.0
    weighted_sum = sum((index + 1) * value for index, value in enumerate(ordered))
    n = len(ordered)
    return (2.0 * weighted_sum) / (n * total) - (n + 1.0) / n


def skewness(values: Iterable[float]) -> float:
    value_list = list(values)
    if len(value_list) < 2:
        return 0.0
    mean = statistics.fmean(value_list)
    variance = statistics.fmean((value - mean) ** 2 for value in value_list)
    if variance <= 0.0:
        return 0.0
    stddev = math.sqrt(variance)
    return statistics.fmean(((value - mean) / stddev) ** 3 for value in value_list)


def top_hotspot_edges(edges: EdgeWeights, k: int = 3) -> set[tuple[str, str]]:
    return {edge for edge, _ in sorted(edges.items(), key=lambda item: (-item[1], item[0]))[:k]}


def top_hotspot_churn(previous: EdgeWeights, current: EdgeWeights, k: int = 3) -> float:
    previous_hotspots = top_hotspot_edges(previous, k)
    current_hotspots = top_hotspot_edges(current, k)
    if not previous_hotspots and not current_hotspots:
        return 0.0
    return 1.0 - (len(previous_hotspots & current_hotspots) / max(1, len(previous_hotspots | current_hotspots)))


def sla_pressure(latency_ms: float, sla_ms: float) -> float:
    return latency_ms / max(1.0, sla_ms)


def sla_violation_ratio(latency_ms: float, sla_ms: float) -> float:
    return max(0.0, (latency_ms - sla_ms) / max(1.0, sla_ms))


def pod_node_occupancy_ratio(non_empty_worker_nodes: int, worker_nodes_selected: int) -> float:
    if worker_nodes_selected <= 0:
        return 0.0
    return non_empty_worker_nodes / worker_nodes_selected


def rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    idx = 0
    while idx < len(ordered):
        end = idx + 1
        while end < len(ordered) and ordered[end][0] == ordered[idx][0]:
            end += 1
        avg_rank = (idx + end + 1) / 2.0
        for _, original in ordered[idx:end]:
            ranks[original] = avg_rank
        idx = end
    return ranks


def pearson(xs: Iterable[float], ys: Iterable[float]) -> float:
    x_values = list(xs)
    y_values = list(ys)
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return 0.0
    mean_x = statistics.fmean(x_values)
    mean_y = statistics.fmean(y_values)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_values))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_values))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def hot_edge_rank_correlation(previous: EdgeWeights, current: EdgeWeights) -> float:
    edges = sorted(set(previous) | set(current))
    if len(edges) < 2:
        return 1.0
    return pearson(
        rank([previous.get(edge, 0.0) for edge in edges]),
        rank([current.get(edge, 0.0) for edge in edges]),
    )


def graph_change_rate(previous: EdgeWeights, current: EdgeWeights, interval_s: float) -> float:
    if interval_s <= 0:
        return 0.0
    return weighted_edge_distance(previous, current) / interval_s
