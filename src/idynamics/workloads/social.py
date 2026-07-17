"""Continuous workload mix generation for iDynamics experiments."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class RequestType:
    name: str
    script_path: str
    url_path: str
    base_latency_ms: float
    sla_ms: float
    edge_weights: Mapping[tuple[str, str], float]
    default_weight: float = 1.0


def default_social_network_requests(base_url: str = "http://nginx-thrift.social-network.svc.cluster.local:8080") -> list[RequestType]:
    script_dir = "external/benchmarks/deathstarbench/socialNetwork/wrk2/scripts/social-network"
    return [
        RequestType(
            name="read_home",
            script_path=f"{script_dir}/read-home-timeline.lua",
            url_path=base_url,
            base_latency_ms=58.0,
            sla_ms=120.0,
            edge_weights={
                ("nginx-thrift", "home-timeline-service"): 1.0,
                ("home-timeline-service", "post-storage-service"): 0.9,
                ("home-timeline-service", "social-graph-service"): 0.7,
                ("home-timeline-service", "user-service"): 0.5,
            },
        ),
        RequestType(
            name="compose_post",
            script_path=f"{script_dir}/compose-post.lua",
            url_path=f"{base_url}/wrk2-api/post/compose",
            base_latency_ms=92.0,
            sla_ms=160.0,
            edge_weights={
                ("nginx-thrift", "compose-post-service"): 1.0,
                ("compose-post-service", "user-service"): 0.6,
                ("compose-post-service", "url-shorten-service"): 0.45,
                ("compose-post-service", "user-mention-service"): 0.45,
                ("compose-post-service", "media-service"): 0.35,
                ("compose-post-service", "post-storage-service"): 0.8,
                ("compose-post-service", "user-timeline-service"): 0.6,
                ("compose-post-service", "home-timeline-service"): 0.7,
            },
        ),
        RequestType(
            name="read_user",
            script_path=f"{script_dir}/read-user-timeline.lua",
            url_path=base_url,
            base_latency_ms=66.0,
            sla_ms=130.0,
            edge_weights={
                ("nginx-thrift", "user-timeline-service"): 1.0,
                ("user-timeline-service", "post-storage-service"): 0.85,
                ("user-timeline-service", "user-service"): 0.55,
            },
        ),
    ]


def default_online_boutique_requests(base_url: str = "http://frontend.online-boutique.svc.cluster.local") -> list[RequestType]:
    """Return Online Boutique request classes with upstream load-generator weights."""
    return [
        RequestType(
            name="index",
            script_path="",
            url_path=f"{base_url}/",
            base_latency_ms=35.0,
            sla_ms=100.0,
            default_weight=1.0,
            edge_weights={
                ("frontend", "productcatalogservice"): 0.5,
                ("frontend", "currencyservice"): 0.3,
                ("frontend", "adservice"): 0.2,
            },
        ),
        RequestType(
            name="setCurrency",
            script_path="",
            url_path=f"{base_url}/setCurrency",
            base_latency_ms=42.0,
            sla_ms=110.0,
            default_weight=2.0,
            edge_weights={
                ("frontend", "currencyservice"): 1.0,
            },
        ),
        RequestType(
            name="browseProduct",
            script_path="",
            url_path=f"{base_url}/product/{{product_id}}",
            base_latency_ms=58.0,
            sla_ms=140.0,
            default_weight=10.0,
            edge_weights={
                ("frontend", "productcatalogservice"): 1.0,
                ("frontend", "recommendationservice"): 0.6,
                ("frontend", "currencyservice"): 0.5,
                ("frontend", "adservice"): 0.35,
                ("recommendationservice", "productcatalogservice"): 0.8,
            },
        ),
        RequestType(
            name="addToCart",
            script_path="",
            url_path=f"{base_url}/cart",
            base_latency_ms=62.0,
            sla_ms=150.0,
            default_weight=2.0,
            edge_weights={
                ("frontend", "cartservice"): 1.0,
                ("frontend", "productcatalogservice"): 0.4,
                ("cartservice", "redis-cart"): 0.9,
            },
        ),
        RequestType(
            name="viewCart",
            script_path="",
            url_path=f"{base_url}/cart",
            base_latency_ms=52.0,
            sla_ms=130.0,
            default_weight=3.0,
            edge_weights={
                ("frontend", "cartservice"): 1.0,
                ("cartservice", "redis-cart"): 0.9,
                ("frontend", "currencyservice"): 0.45,
            },
        ),
        RequestType(
            name="checkout",
            script_path="",
            url_path=f"{base_url}/cart/checkout",
            base_latency_ms=95.0,
            sla_ms=220.0,
            default_weight=1.0,
            edge_weights={
                ("frontend", "checkoutservice"): 1.0,
                ("checkoutservice", "cartservice"): 0.8,
                ("cartservice", "redis-cart"): 0.7,
                ("checkoutservice", "paymentservice"): 0.7,
                ("checkoutservice", "shippingservice"): 0.6,
                ("checkoutservice", "emailservice"): 0.4,
                ("checkoutservice", "currencyservice"): 0.4,
                ("checkoutservice", "productcatalogservice"): 0.4,
            },
        ),
    ]


def default_moe_requests(base_url: str = "http://frontend.moe.svc.cluster.local:8080") -> list[RequestType]:
    """Return CPU-only MoE-style serving request classes."""
    return [
        RequestType(
            name="single_expert",
            script_path="",
            url_path=f"{base_url}/infer?top_k=1",
            base_latency_ms=34.0,
            sla_ms=95.0,
            edge_weights={
                ("frontend", "tokenizer"): 0.7,
                ("frontend", "router"): 1.0,
                ("router", "expert-0"): 1.0,
                ("expert-0", "aggregator"): 0.9,
                ("aggregator", "cache"): 0.25,
            },
        ),
        RequestType(
            name="multi_expert_top2",
            script_path="",
            url_path=f"{base_url}/infer?top_k=2",
            base_latency_ms=49.0,
            sla_ms=125.0,
            edge_weights={
                ("frontend", "tokenizer"): 0.7,
                ("frontend", "router"): 1.0,
                ("router", "expert-0"): 0.9,
                ("router", "expert-1"): 0.9,
                ("expert-0", "aggregator"): 0.8,
                ("expert-1", "aggregator"): 0.8,
                ("aggregator", "cache"): 0.25,
            },
        ),
        RequestType(
            name="multi_expert_top4",
            script_path="",
            url_path=f"{base_url}/infer?top_k=4",
            base_latency_ms=73.0,
            sla_ms=170.0,
            edge_weights={
                ("frontend", "tokenizer"): 0.7,
                ("frontend", "router"): 1.0,
                ("router", "expert-0"): 0.7,
                ("router", "expert-1"): 0.7,
                ("router", "expert-2"): 0.7,
                ("router", "expert-3"): 0.7,
                ("expert-0", "aggregator"): 0.6,
                ("expert-1", "aggregator"): 0.6,
                ("expert-2", "aggregator"): 0.6,
                ("expert-3", "aggregator"): 0.6,
            },
        ),
        RequestType(
            name="cache_hit",
            script_path="",
            url_path=f"{base_url}/infer?cache=hit",
            base_latency_ms=23.0,
            sla_ms=80.0,
            edge_weights={
                ("frontend", "tokenizer"): 0.35,
                ("frontend", "router"): 0.45,
                ("router", "cache"): 1.0,
                ("cache", "aggregator"): 0.7,
            },
        ),
        RequestType(
            name="cache_miss",
            script_path="",
            url_path=f"{base_url}/infer?cache=miss",
            base_latency_ms=65.0,
            sla_ms=150.0,
            edge_weights={
                ("frontend", "tokenizer"): 0.7,
                ("frontend", "router"): 1.0,
                ("router", "cache"): 0.5,
                ("router", "expert-0"): 0.8,
                ("router", "expert-1"): 0.8,
                ("expert-0", "aggregator"): 0.7,
                ("expert-1", "aggregator"): 0.7,
            },
        ),
        RequestType(
            name="payload_small",
            script_path="",
            url_path=f"{base_url}/infer?payload=small",
            base_latency_ms=38.0,
            sla_ms=100.0,
            edge_weights={
                ("frontend", "tokenizer"): 0.45,
                ("frontend", "router"): 0.65,
                ("router", "expert-0"): 0.55,
                ("expert-0", "aggregator"): 0.5,
            },
        ),
        RequestType(
            name="payload_large",
            script_path="",
            url_path=f"{base_url}/infer?payload=large",
            base_latency_ms=84.0,
            sla_ms=190.0,
            edge_weights={
                ("frontend", "tokenizer"): 1.0,
                ("frontend", "router"): 1.4,
                ("router", "expert-0"): 1.2,
                ("router", "expert-1"): 1.2,
                ("expert-0", "aggregator"): 1.1,
                ("expert-1", "aggregator"): 1.1,
            },
        ),
        RequestType(
            name="batch_small",
            script_path="",
            url_path=f"{base_url}/infer?batch=small",
            base_latency_ms=45.0,
            sla_ms=115.0,
            edge_weights={
                ("frontend", "tokenizer"): 0.65,
                ("frontend", "router"): 0.8,
                ("router", "expert-0"): 0.7,
                ("expert-0", "aggregator"): 0.65,
            },
        ),
        RequestType(
            name="batch_large",
            script_path="",
            url_path=f"{base_url}/infer?batch=large",
            base_latency_ms=98.0,
            sla_ms=230.0,
            edge_weights={
                ("frontend", "tokenizer"): 1.2,
                ("frontend", "router"): 1.5,
                ("router", "expert-0"): 1.1,
                ("router", "expert-1"): 1.1,
                ("router", "expert-2"): 1.1,
                ("expert-0", "aggregator"): 1.0,
                ("expert-1", "aggregator"): 1.0,
                ("expert-2", "aggregator"): 1.0,
            },
        ),
    ]


WORKLOAD_ALIASES = {
    "social": "social-network",
    "social_network": "social-network",
    "social-network": "social-network",
    "online_boutique": "online-boutique",
    "online-boutique": "online-boutique",
    "boutique": "online-boutique",
    "moe": "moe-serving",
    "moe_serving": "moe-serving",
    "moe-serving": "moe-serving",
}


def normalize_workload_mode(workload_mode: str) -> str:
    normalized = workload_mode.strip().lower().replace(" ", "-")
    return WORKLOAD_ALIASES.get(normalized, normalized)


def default_requests_for_workload(workload_mode: str, base_url: str | None = None) -> list[RequestType]:
    normalized = normalize_workload_mode(workload_mode)
    if normalized == "social-network":
        return default_social_network_requests() if base_url is None else default_social_network_requests(base_url)
    if normalized == "online-boutique":
        return default_online_boutique_requests() if base_url is None else default_online_boutique_requests(base_url)
    if normalized == "moe-serving":
        return default_moe_requests() if base_url is None else default_moe_requests(base_url)
    raise ValueError(f"unsupported workload_mode: {workload_mode}")


class WorkloadMixer:
    """Generate time-varying probabilities for concurrent request types."""

    def __init__(
        self,
        request_names: Iterable[str] | None = None,
        mode: str = "sinusoidal",
        steps: int = 500,
        interval_s: float = 5.0,
        seed: int = 7,
        trace_csv: str | Path | None = None,
        qps: float = 90.0,
        workload_mode: str = "social-network",
        default_weights: Mapping[str, float] | None = None,
        base_url: str | None = None,
    ) -> None:
        self.workload_mode = normalize_workload_mode(workload_mode)
        self.request_types = default_requests_for_workload(self.workload_mode, base_url=base_url)
        if request_names is None:
            self.request_names = [request.name for request in self.request_types]
        else:
            self.request_names = list(request_names)
        self.mode = mode
        self.steps = steps
        self.interval_s = interval_s
        self.seed = seed
        self.qps = qps
        self.random = random.Random(seed)
        self.trace_rows = self._load_trace(trace_csv) if trace_csv else []
        if len(self.request_names) < 2:
            raise ValueError("WorkloadMixer requires at least two request types")
        if self.steps <= 0:
            raise ValueError("WorkloadMixer requires steps > 0")
        if self.interval_s < 0:
            raise ValueError("WorkloadMixer requires interval_s >= 0")
        type_weights = {request.name: request.default_weight for request in self.request_types}
        if default_weights is not None:
            type_weights.update({name: float(weight) for name, weight in default_weights.items()})
        self.default_weights = {name: max(0.0, float(type_weights.get(name, 1.0))) for name in self.request_names}
        self.default_mix = self._normalize(self.default_weights)
        self._markov_states = self._build_markov_states()

    def probabilities(self, step: int) -> dict[str, float]:
        if self.mode == "step":
            return self._step(step)
        if self.mode == "linear":
            return self._linear(step)
        if self.mode == "sinusoidal":
            return self._sinusoidal(step)
        if self.mode == "markov":
            return self._markov(step)
        if self.mode == "expert_skew_shift":
            return self._linear(step)
        if self.mode == "cache_stress":
            return self._named_stress({"cache_hit": 0.56, "cache_miss": 0.32}, step)
        if self.mode == "payload_heavy":
            return self._named_stress({"payload_large": 0.42, "batch_large": 0.32, "multi_expert_top4": 0.16}, step)
        if self.mode == "trace_csv":
            return self._trace_csv(step)
        raise ValueError(f"unsupported workload mixer mode: {self.mode}")

    def schedule(self) -> list[dict[str, float]]:
        return [self.probabilities(step) for step in range(self.steps)]

    def qps_for_step(self, step: int) -> dict[str, float]:
        probabilities = self.probabilities(step)
        return {name: self.qps * probabilities[name] for name in self.request_names}

    def mode_rows(self, modes: Iterable[str] = ("step", "linear", "sinusoidal", "markov")) -> list[dict[str, float | int | str]]:
        rows: list[dict[str, float | int | str]] = []
        for mode in modes:
            mixer = WorkloadMixer(
                request_names=self.request_names,
                mode=mode,
                steps=self.steps,
                interval_s=self.interval_s,
                seed=self.seed,
                qps=self.qps,
                workload_mode=self.workload_mode,
                default_weights=self.default_weights,
            )
            for step, probabilities in enumerate(mixer.schedule()):
                rows.append({"mode": mode, "step": step, **{f"p_{name}": probabilities[name] for name in self.request_names}})
        return rows

    def request_mix_rows(self, include_metrics: bool = True) -> list[dict[str, str | int]]:
        rows: list[dict[str, str | int]] = []
        for step, probabilities in enumerate(self.schedule()):
            row: dict[str, str | int] = {
                "step": step,
                "time_s": f"{step * self.interval_s:.3f}",
                **{f"p_{name}": f"{probabilities[name]:.6f}" for name in self.request_names},
                **{f"qps_{name}": f"{self.qps * probabilities[name]:.6f}" for name in self.request_names},
            }
            if include_metrics:
                row.update(
                    {
                        "traffic_stress": "",
                        "edge_jaccard_distance": "",
                        "weighted_edge_distance": "",
                        "hot_edge_rank_correlation": "",
                        "graph_change_rate_per_s": "",
                        "request_mix_entropy": "",
                        "top3_hotspot_churn": "",
                        "active_edge_count": "",
                        "traffic_stress_gini": "",
                        "traffic_stress_skew": "",
                        "migration_count": "",
                        "policy_decision_time_ms": "",
                        "latency_ms": "",
                        "sla_ms": "",
                        "sla_pressure": "",
                        "sla_violation_ratio": "",
                    }
                )
            rows.append(row)
        return rows

    def workload_mixer_modes_fieldnames(self) -> list[str]:
        return ["mode", "step", *[f"p_{name}" for name in self.request_names]]

    def request_mix_fieldnames(self, include_metrics: bool = True) -> list[str]:
        fields = [
            "step",
            "time_s",
            *[f"p_{name}" for name in self.request_names],
            *[f"qps_{name}" for name in self.request_names],
        ]
        if include_metrics:
            fields.extend(
                [
                    "traffic_stress",
                    "edge_jaccard_distance",
                    "weighted_edge_distance",
                    "hot_edge_rank_correlation",
                    "graph_change_rate_per_s",
                    "request_mix_entropy",
                    "top3_hotspot_churn",
                    "active_edge_count",
                    "traffic_stress_gini",
                    "traffic_stress_skew",
                    "migration_count",
                    "policy_decision_time_ms",
                    "latency_ms",
                    "sla_ms",
                    "sla_pressure",
                    "sla_violation_ratio",
                ]
            )
        return fields

    def write_artifacts(self, output_dir: str | Path, include_metrics: bool = True) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self._write_csv(output_path / "workload_mixer_modes.csv", self.workload_mixer_modes_fieldnames(), self.mode_rows())
        self._write_csv(
            output_path / "request_mix_timeseries.csv",
            self.request_mix_fieldnames(include_metrics=include_metrics),
            self.request_mix_rows(include_metrics=include_metrics),
        )

    def _normalize(self, values: Mapping[str, float]) -> dict[str, float]:
        clipped = {name: max(0.0, float(values.get(name, 0.0))) for name in self.request_names}
        total = sum(clipped.values())
        if total <= 0:
            return {name: 1.0 / len(self.request_names) for name in self.request_names}
        return {name: value / total for name, value in clipped.items()}

    def _step(self, step: int) -> dict[str, float]:
        segment = max(1, self.steps // len(self.request_names))
        dominant = min(len(self.request_names) - 1, step // segment)
        values = {name: 0.30 * self.default_mix[name] for name in self.request_names}
        values[self.request_names[dominant]] = values[self.request_names[dominant]] + 0.70
        return self._normalize(values)

    def _linear(self, step: int) -> dict[str, float]:
        progress = step / max(1, self.steps - 1)
        names = self.request_names
        start = {name: 0.30 * self.default_mix[name] for name in names}
        start[names[0]] = start[names[0]] + 0.70
        end = {name: 0.30 * self.default_mix[name] for name in names}
        end[names[-1]] = end[names[-1]] + 0.70
        values = {name: start[name] * (1.0 - progress) + end[name] * progress for name in names}
        if len(names) > 2:
            middle = names[len(names) // 2]
            values[middle] = values[middle] + 0.20 * math.sin(math.pi * progress)
        return self._normalize(values)

    def _sinusoidal(self, step: int) -> dict[str, float]:
        phase = 2.0 * math.pi * step / max(1, self.steps)
        values = {}
        for index, name in enumerate(self.request_names):
            shifted = phase + 2.0 * math.pi * index / len(self.request_names)
            values[name] = self.default_mix[name] * (1.0 + 0.72 * math.sin(shifted))
        return self._normalize(values)

    def _markov(self, step: int) -> dict[str, float]:
        state = self._markov_states[min(step, len(self._markov_states) - 1)]
        values = {name: 0.35 * self.default_mix[name] for name in self.request_names}
        values[self.request_names[state]] = values[self.request_names[state]] + 0.65
        return self._normalize(values)

    def _named_stress(self, boosts: Mapping[str, float], step: int) -> dict[str, float]:
        wave = 0.5 + 0.5 * math.sin(2.0 * math.pi * step / max(1, self.steps))
        values = {name: 0.35 * self.default_mix[name] for name in self.request_names}
        for name, boost in boosts.items():
            if name in values:
                values[name] = values[name] + boost * (0.55 + 0.45 * wave)
        if all(name not in values for name in boosts):
            return self._sinusoidal(step)
        return self._normalize(values)

    def _build_markov_states(self) -> list[int]:
        state = 0
        states = []
        for _ in range(self.steps):
            if self.random.random() < 0.24:
                state = self.random.randrange(len(self.request_names))
            states.append(state)
        return states

    def _trace_csv(self, step: int) -> dict[str, float]:
        if not self.trace_rows:
            raise ValueError("trace_csv mode requires a non-empty CSV trace")
        return self._normalize(self.trace_rows[min(step, len(self.trace_rows) - 1)])

    def _load_trace(self, trace_csv: str | Path | None) -> list[dict[str, float]]:
        if trace_csv is None:
            return []
        with Path(trace_csv).open(newline="") as input_file:
            reader = csv.DictReader(input_file)
            rows = []
            for row in reader:
                values = {}
                for name in self.request_names:
                    values[name] = float(row.get(name, row.get(f"p_{name}", 0.0)) or 0.0)
                rows.append(values)
            return rows

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[Mapping]) -> None:
        with path.open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
