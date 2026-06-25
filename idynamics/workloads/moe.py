"""Pure MoE-style workload and placement helpers."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping


SERVICES = ["frontend", "tokenizer", "router", "aggregator", "cache"]

REQUEST_TYPES = [
    "single_expert",
    "multi_expert_top2",
    "multi_expert_top4",
    "cache_hit",
    "cache_miss",
    "payload_small",
    "payload_large",
    "batch_small",
    "batch_large",
]

WORKLOAD_MODES = [
    "step",
    "linear",
    "sinusoidal",
    "markov",
    "expert_skew_shift",
    "cache_stress",
    "payload_heavy",
]


def normalize(values: list[float]) -> list[float]:
    total = sum(max(0.0, value) for value in values)
    if total <= 0:
        return [1.0 / len(values) for _ in values]
    return [max(0.0, value) / total for value in values]


def weights_for_step(experts: int, step: int, total_steps: int, mode: str, alpha: float) -> list[float]:
    mode = mode.replace("_", "-")
    rank_weights = [1.0 / ((rank + 1) ** alpha) for rank in range(experts)]
    if mode in {"stable", "step"}:
        segment = max(1, total_steps // 3)
        hot = min(experts - 1, (step // segment) % max(1, experts))
        rotated = [0.10 for _ in range(experts)]
        rotated[hot] = 1.0
    elif mode == "linear":
        offset = (step * experts) // max(1, total_steps)
        rotated = rank_weights[offset:] + rank_weights[:offset]
    elif mode == "expert-skew-shift":
        offset = (step * experts) // max(1, total_steps)
        rotated = [0.06 for _ in range(experts)]
        rotated[offset % experts] = 1.2
        rotated[(offset + 1) % experts] = 0.55
    elif mode in {"cache-stress", "payload-heavy"}:
        rotated = rank_weights
    elif mode == "sinusoidal":
        hot = int(((math.sin(2.0 * math.pi * step / max(1, total_steps)) + 1.0) / 2.0) * (experts - 1))
        rotated = [0.12 for _ in range(experts)]
        rotated[hot] = 1.0
    elif mode == "markov":
        rng = random.Random(7919 + experts * 101 + int(alpha * 1000))
        hot = 0
        for _ in range(step + 1):
            if rng.random() < 0.22:
                hot = rng.randrange(experts)
            elif rng.random() < 0.55:
                hot = (hot + rng.choice([-1, 1])) % experts
        rotated = [0.08 for _ in range(experts)]
        rotated[hot] = 1.05
        rotated[(hot + 1) % experts] = 0.36
    elif mode == "burst":
        hot = 0 if (step // max(1, total_steps // 4)) % 2 == 0 else experts - 1
        rotated = [0.04 for _ in range(experts)]
        rotated[hot] = 1.5
    else:
        offset = (step * experts) // max(1, total_steps)
        rotated = rank_weights[offset:] + rank_weights[:offset]
    return normalize(rotated)


def default_placement(experts: int, nodes: int) -> dict[str, int]:
    names = [*SERVICES, *[f"expert-{idx}" for idx in range(experts)]]
    return {name: idx % nodes for idx, name in enumerate(names)}


def idynamics_placement(experts: int, nodes: int, weights: list[float], top_k: int) -> dict[str, int]:
    hot = sorted(range(experts), key=lambda idx: weights[idx], reverse=True)[: max(1, top_k)]
    placement: dict[str, int] = {}
    hot_node = 0
    for name in SERVICES:
        placement[name] = hot_node
    for expert in range(experts):
        if expert in hot:
            placement[f"expert-{expert}"] = hot_node
        else:
            placement[f"expert-{expert}"] = 1 + ((expert - len(hot)) % max(1, nodes - 1)) if nodes > 1 else 0
    return placement


def policy_placement(policy: str, experts: int, nodes: int, weights: list[float], top_k: int) -> dict[str, int]:
    """Return deterministic MoE placements matching the paper-facing policy intent."""
    normalized = policy.lower()
    if normalized in {"default", "kubernetes", "kubernetes-default"}:
        return default_placement(experts, nodes)
    hot = sorted(range(experts), key=lambda idx: weights[idx], reverse=True)[: max(1, top_k)]
    if normalized in {"idynamics", "policy1", "p1"}:
        return idynamics_placement(experts, nodes, weights, top_k)
    placement: dict[str, int] = {}
    last = max(0, nodes - 1)
    if normalized in {"policy2", "p2"}:
        for name in SERVICES:
            placement[name] = 0
        for expert in range(experts):
            placement[f"expert-{expert}"] = 0 if expert in hot else min(last, 1 + expert % max(1, nodes - 1))
        return placement
    if normalized in {"policy3", "p3"}:
        # Keep payload-heavy fan-out/fan-in actors together, but leave lightweight
        # frontend/tokenizer/cache off the payload lane when capacity exists.
        payload_node = 0
        support_node = 1 if nodes > 1 else 0
        for name in ("router", "aggregator"):
            placement[name] = payload_node
        for name in ("frontend", "tokenizer", "cache"):
            placement[name] = support_node
        for expert in range(experts):
            placement[f"expert-{expert}"] = payload_node if expert in hot else min(last, 1 + expert % max(1, nodes - 1))
        return placement
    if normalized in {"policy4", "p4"}:
        hybrid_node = 0
        cache_node = 1 if nodes > 1 else 0
        for name in ("frontend", "tokenizer", "router", "aggregator"):
            placement[name] = hybrid_node
        placement["cache"] = cache_node
        for expert in range(experts):
            placement[f"expert-{expert}"] = hybrid_node if expert in hot else min(last, 1 + expert % max(1, nodes - 1))
        return placement
    raise ValueError(f"unknown MoE placement policy {policy!r}")


def edge_cost(src: str, dst: str, placement: Mapping[str, int]) -> float:
    if placement[src] == placement[dst]:
        return 1.0
    return 1.0 + abs(placement[src] - placement[dst]) * 0.35


def traffic_edges(weights: list[float], requests: int, top_k: int, payload_bytes: int) -> dict[tuple[str, str], float]:
    edges: dict[tuple[str, str], float] = {
        ("frontend", "tokenizer"): requests * 64.0,
        ("frontend", "router"): requests * 96.0,
        ("aggregator", "cache"): requests * 32.0,
    }
    selected_mass = sum(sorted(weights, reverse=True)[: max(1, top_k)])
    for expert, weight in enumerate(weights):
        expert_requests = requests * top_k * weight / max(0.000001, selected_mass)
        edges[("router", f"expert-{expert}")] = expert_requests * (128.0 + payload_bytes)
        edges[(f"expert-{expert}", "aggregator")] = expert_requests * (128.0 + payload_bytes)
    return edges


def placement_cost(edges: Mapping[tuple[str, str], float], placement: Mapping[str, int]) -> float:
    return sum(weight * edge_cost(src, dst, placement) for (src, dst), weight in edges.items())


def latency_model(cost: float, baseline_cost: float, compute_delay_ms: float, rng: random.Random) -> float:
    network_ms = 8.0 * (cost / max(1.0, baseline_cost))
    return max(1.0, compute_delay_ms * 4.0 + network_ms + rng.gauss(0.0, 0.8))
