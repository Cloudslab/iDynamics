#!/usr/bin/env python3
"""Workload generator for MoE expert-skew experiments."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from idynamics.workloads.moe import REQUEST_TYPES, WORKLOAD_MODES, weights_for_step


REQUEST_TYPE_PROFILES: dict[str, dict[str, Any]] = {
    "single_expert": {"top_k": 1, "cache_hit_ratio": 0.0, "payload_bytes": 256, "batch_size": 1},
    "multi_expert_top2": {"top_k": 2, "cache_hit_ratio": 0.0, "payload_bytes": 512, "batch_size": 1},
    "multi_expert_top4": {"top_k": 4, "cache_hit_ratio": 0.0, "payload_bytes": 768, "batch_size": 1},
    "cache_hit": {"top_k": 1, "cache_hit_ratio": 1.0, "payload_bytes": 128, "batch_size": 1},
    "cache_miss": {"top_k": 2, "cache_hit_ratio": 0.0, "payload_bytes": 512, "batch_size": 1},
    "payload_small": {"top_k": 1, "cache_hit_ratio": 0.0, "payload_bytes": 128, "batch_size": 1},
    "payload_large": {"top_k": 2, "cache_hit_ratio": 0.0, "payload_bytes": 4096, "batch_size": 1},
    "batch_small": {"top_k": 1, "cache_hit_ratio": 0.0, "payload_bytes": 512, "batch_size": 4},
    "batch_large": {"top_k": 3, "cache_hit_ratio": 0.0, "payload_bytes": 2048, "batch_size": 16},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://frontend.moe-serving.svc.cluster.local:8080/infer")
    parser.add_argument("--experts", type=int, default=4)
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--qps", type=float, default=20.0)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument(
        "--skew-mode",
        choices=["stable", "phase-shift", "phase_shift", "burst", *WORKLOAD_MODES],
        default="phase_shift",
    )
    parser.add_argument("--request-type", choices=["mixed", *REQUEST_TYPES], default="mixed")
    parser.add_argument("--zipf-alpha", type=float, default=1.2)
    parser.add_argument("--compute-delay-ms", type=float, default=5.0)
    parser.add_argument("--payload-bytes", type=int, default=256)
    parser.add_argument("--cache-hit-ratio", type=float, default=0.0)
    parser.add_argument("--cache-key-space", type=int, default=128)
    parser.add_argument("--sla-ms", type=float, default=500.0)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def selected_experts(weights: list[float], top_k: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    local_weights = list(weights)
    selected: list[int] = []
    for _ in range(max(1, min(top_k, len(weights)))):
        total = sum(local_weights)
        if total <= 0.0:
            selected.append(len(selected) % len(weights))
            continue
        draw = rng.random() * total
        cursor = 0.0
        for idx, weight in enumerate(local_weights):
            cursor += weight
            if draw <= cursor:
                selected.append(idx)
                local_weights[idx] = 0.0
                break
    return selected


def request_type_for_request(args: argparse.Namespace, request_id: int) -> str:
    if args.request_type != "mixed":
        return args.request_type
    if args.skew_mode.replace("_", "-") == "cache-stress":
        return "cache_hit" if request_id % 3 else "cache_miss"
    if args.skew_mode.replace("_", "-") == "payload-heavy":
        return "payload_large" if request_id % 4 else "batch_large"
    return REQUEST_TYPES[request_id % len(REQUEST_TYPES)]


def effective_profile(args: argparse.Namespace, request_type: str) -> dict[str, Any]:
    profile = dict(REQUEST_TYPE_PROFILES[request_type])
    if args.request_type == "mixed":
        return profile
    profile["top_k"] = args.top_k
    profile["payload_bytes"] = args.payload_bytes
    profile["cache_hit_ratio"] = args.cache_hit_ratio
    return profile


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def post_json(url: str, payload: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    rows: list[dict[str, Any]] = []
    interval = 1.0 / args.qps if args.qps > 0 else 0.0
    for request_id in range(args.requests):
        request_type = request_type_for_request(args, request_id)
        profile = effective_profile(args, request_type)
        weights = weights_for_step(args.experts, request_id, args.requests, args.skew_mode, args.zipf_alpha)
        phase = request_id // max(1, args.requests // max(1, args.experts))
        payload = {
            "request_id": request_id,
            "phase": phase,
            "request_type": request_type,
            "prompt": f"request {request_id} " + ("token " * rng.randint(4, 16)),
            "expert_popularity": ",".join(f"{weight:.8f}" for weight in weights),
            "compute_delay_ms": args.compute_delay_ms * max(1, int(profile["batch_size"])) ** 0.5,
            "payload_bytes": int(profile["payload_bytes"]),
            "cache_hit_ratio": float(profile["cache_hit_ratio"]),
            "cache_key_space": args.cache_key_space,
            "cache_key": f"prompt-{request_id % max(1, args.cache_key_space)}",
            "top_k": int(profile["top_k"]),
            "batch_size": int(profile["batch_size"]),
        }
        started = time.perf_counter()
        status = "dry-run"
        experts = ""
        error = ""
        if not args.dry_run:
            try:
                response = post_json(args.url, payload)
                status = "200"
                experts = ",".join(str(item) for item in response.get("result", {}).get("experts", []))
                if response.get("cached"):
                    experts = "cache-hit"
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                status = "error"
                error = str(exc)
        else:
            experts = ",".join(str(item) for item in selected_experts(weights, int(profile["top_k"]), request_id + phase * 1000003))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        rows.append(
            {
                "request_id": request_id,
                "request_type": request_type,
                "status": status,
                "latency_ms": f"{elapsed_ms:.6f}",
                "experts": experts,
                "top_k": int(profile["top_k"]),
                "payload_bytes": int(profile["payload_bytes"]),
                "batch_size": int(profile["batch_size"]),
                "cache_intent": "hit" if float(profile["cache_hit_ratio"]) >= 1.0 else "miss" if request_type == "cache_miss" else "normal",
                "hot_expert": max(range(args.experts), key=lambda idx: weights[idx]),
                "expert_popularity": ";".join(f"{weight:.6f}" for weight in weights),
                "cache_key": payload["cache_key"],
                "error": error,
            }
        )
        if interval > 0:
            time.sleep(max(0.0, interval - (time.perf_counter() - started)))
    if args.output:
        write_rows(Path(args.output), rows)
    latencies = [float(row["latency_ms"]) for row in rows]
    successful = [float(row["latency_ms"]) for row in rows if row["status"] in {"200", "dry-run"}]
    errors = sum(1 for row in rows if row["status"] not in {"200", "dry-run"})
    elapsed_s = sum(latencies) / 1000.0 if args.dry_run else max(0.000001, args.requests / max(args.qps, 0.000001))
    print(
        json.dumps(
            {
                "requests": len(rows),
                "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
                "mean_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
                "p50_latency_ms": percentile(successful, 50),
                "p95_latency_ms": percentile(successful, 95),
                "p99_latency_ms": percentile(successful, 99),
                "throughput_rps": len(successful) / elapsed_s if elapsed_s > 0.0 else 0.0,
                "sla_violations": sum(1 for value in successful if value > args.sla_ms) + errors,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
