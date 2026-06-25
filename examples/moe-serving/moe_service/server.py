#!/usr/bin/env python3
"""Role-selectable HTTP service for the MoE serving microbenchmark."""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


ROLE = os.getenv("MOE_ROLE", "frontend")
SERVICE_NAME = os.getenv("SERVICE_NAME", ROLE)
PORT = int(os.getenv("PORT", "8080"))
EXPERT_ID = int(os.getenv("EXPERT_ID", "0"))
EXPERTS = int(os.getenv("EXPERTS", "4"))
PAYLOAD_BYTES = int(os.getenv("PAYLOAD_BYTES", "256"))
COMPUTE_DELAY_MS = float(os.getenv("COMPUTE_DELAY_MS", "5"))
EXPERT_DELAY_MS = float(os.getenv("EXPERT_DELAY_MS", str(COMPUTE_DELAY_MS)))
EXPERT_BASE_URL = os.getenv("EXPERT_BASE_URL", "http://expert-{id}:8080")
TOKENIZER_URL = os.getenv("TOKENIZER_URL", "http://tokenizer:8080")
ROUTER_URL = os.getenv("ROUTER_URL", "http://router:8080")
AGGREGATOR_URL = os.getenv("AGGREGATOR_URL", "http://aggregator:8080")
CACHE_URL = os.getenv("CACHE_URL", "http://cache:8080")
DEFAULT_POPULARITY = os.getenv("EXPERT_POPULARITY", "")
TOP_K = int(os.getenv("TOP_K", "2"))
CACHE_HIT_RATIO = float(os.getenv("CACHE_HIT_RATIO", "0.0"))
CACHE_KEY_SPACE = int(os.getenv("CACHE_KEY_SPACE", "128"))


class Metrics:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests: dict[tuple[str, str], int] = {}
        self.latency_sum: dict[str, float] = {}
        self.latency_count: dict[str, int] = {}
        self.bytes_sent = 0
        self.expert_hits: dict[int, int] = {}
        self.cache_events: dict[str, int] = {}

    def observe(self, route: str, status: str, latency_ms: float, bytes_sent: int = 0, expert: int | None = None) -> None:
        with self.lock:
            key = (route, status)
            self.requests[key] = self.requests.get(key, 0) + 1
            self.latency_sum[route] = self.latency_sum.get(route, 0.0) + latency_ms
            self.latency_count[route] = self.latency_count.get(route, 0) + 1
            self.bytes_sent += bytes_sent
            if expert is not None:
                self.expert_hits[expert] = self.expert_hits.get(expert, 0) + 1

    def render(self) -> str:
        lines = [
            "# HELP moe_requests_total Total MoE service requests.",
            "# TYPE moe_requests_total counter",
        ]
        with self.lock:
            for (route, status), value in sorted(self.requests.items()):
                lines.append(
                    f'moe_requests_total{{service="{SERVICE_NAME}",role="{ROLE}",route="{route}",status="{status}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP moe_request_latency_ms_sum Sum of request latency in milliseconds.",
                    "# TYPE moe_request_latency_ms_sum counter",
                ]
            )
            for route, value in sorted(self.latency_sum.items()):
                lines.append(f'moe_request_latency_ms_sum{{service="{SERVICE_NAME}",role="{ROLE}",route="{route}"}} {value:.6f}')
            lines.append("# HELP moe_request_latency_ms_count Count of latency observations.")
            lines.append("# TYPE moe_request_latency_ms_count counter")
            for route, value in sorted(self.latency_count.items()):
                lines.append(f'moe_request_latency_ms_count{{service="{SERVICE_NAME}",role="{ROLE}",route="{route}"}} {value}')
            lines.append("# HELP moe_payload_bytes_total Total response payload bytes.")
            lines.append("# TYPE moe_payload_bytes_total counter")
            lines.append(f'moe_payload_bytes_total{{service="{SERVICE_NAME}",role="{ROLE}"}} {self.bytes_sent}')
            lines.append("# HELP moe_expert_hits_total Expert selections.")
            lines.append("# TYPE moe_expert_hits_total counter")
            for expert, value in sorted(self.expert_hits.items()):
                lines.append(f'moe_expert_hits_total{{service="{SERVICE_NAME}",role="{ROLE}",expert="{expert}"}} {value}')
            lines.append("# HELP moe_cache_events_total Cache hit and miss events.")
            lines.append("# TYPE moe_cache_events_total counter")
            for outcome, value in sorted(self.cache_events.items()):
                lines.append(f'moe_cache_events_total{{service="{SERVICE_NAME}",role="{ROLE}",outcome="{outcome}"}} {value}')
        return "\n".join(lines) + "\n"

    def observe_cache(self, outcome: str) -> None:
        with self.lock:
            self.cache_events[outcome] = self.cache_events.get(outcome, 0) + 1


METRICS = Metrics()
CACHE: dict[str, Any] = {}


def parse_popularity(value: str) -> list[float]:
    if not value:
        return [1.0 / EXPERTS for _ in range(EXPERTS)]
    weights = [max(0.0, float(part)) for part in value.split(",") if part.strip()]
    if len(weights) < EXPERTS:
        weights.extend([0.0] * (EXPERTS - len(weights)))
    weights = weights[:EXPERTS]
    total = sum(weights)
    return [1.0 / EXPERTS for _ in range(EXPERTS)] if total <= 0 else [weight / total for weight in weights]


def post_json(url: str, payload: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def weighted_experts(weights: list[float], top_k: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    candidates = list(range(len(weights)))
    selected: list[int] = []
    local_weights = list(weights)
    for _ in range(max(1, min(top_k, len(candidates)))):
        total = sum(local_weights)
        if total <= 0:
            selected.append(candidates[len(selected) % len(candidates)])
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


def sleep_ms(delay_ms: float) -> None:
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)


class Handler(BaseHTTPRequestHandler):
    server_version = "moe-serving/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.write_json({"ok": True, "role": ROLE})
            return
        if self.path == "/metrics":
            body = METRICS.render().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        started = time.perf_counter()
        status = "200"
        try:
            payload = self.read_json()
            if ROLE == "frontend":
                result = self.handle_frontend(payload)
            elif ROLE == "tokenizer":
                result = self.handle_tokenizer(payload)
            elif ROLE == "router":
                result = self.handle_router(payload)
            elif ROLE == "expert":
                result = self.handle_expert(payload)
            elif ROLE == "aggregator":
                result = self.handle_aggregator(payload)
            elif ROLE == "cache":
                result = self.handle_cache(payload)
            else:
                raise ValueError(f"unsupported role {ROLE}")
            body_bytes = self.write_json(result)
        except (ValueError, urllib.error.URLError, TimeoutError) as exc:
            status = "500"
            body_bytes = self.write_json({"ok": False, "error": str(exc)}, code=500)
        elapsed = (time.perf_counter() - started) * 1000.0
        METRICS.observe(self.path, status, elapsed, body_bytes)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def write_json(self, payload: dict[str, Any], code: int = 200) -> int:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return len(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def handle_frontend(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_type = str(payload.get("request_type", ""))
        cache_hit_ratio = float(payload.get("cache_hit_ratio", CACHE_HIT_RATIO))
        request_id = int(payload.get("request_id", 0))
        cache_key_space = max(1, int(payload.get("cache_key_space", CACHE_KEY_SPACE)))
        cache_key = str(payload.get("cache_key", f"prompt-{request_id % cache_key_space}"))
        if request_type == "cache_hit":
            post_json(f"{CACHE_URL}/put", {"key": cache_key, "value": {"experts": [], "bytes": 0, "request_type": request_type}})
            cache_hit_ratio = 1.0
        elif request_type == "cache_miss":
            cache_key = f"{cache_key}-miss-{request_id}"
            payload = {**payload, "cache_key": cache_key}
            cache_hit_ratio = 1.0
        should_probe_cache = random.Random(request_id + 99173).random() < cache_hit_ratio
        if should_probe_cache:
            cached = post_json(f"{CACHE_URL}/get", {"key": cache_key})
            if cached.get("hit"):
                METRICS.observe_cache("hit")
                return {"ok": True, "cached": True, "result": cached.get("value")}
            METRICS.observe_cache("miss")
        tokenized = post_json(f"{TOKENIZER_URL}/tokenize", payload)
        routed = post_json(f"{ROUTER_URL}/route", tokenized)
        return {"ok": True, "result": routed}

    def handle_tokenizer(self, payload: dict[str, Any]) -> dict[str, Any]:
        sleep_ms(COMPUTE_DELAY_MS)
        prompt = str(payload.get("prompt", ""))
        tokens = max(1, len(prompt.split()))
        return {**payload, "tokens": tokens, "tokenizer": SERVICE_NAME}

    def handle_router(self, payload: dict[str, Any]) -> dict[str, Any]:
        weights = parse_popularity(str(payload.get("expert_popularity", DEFAULT_POPULARITY)))
        seed = int(payload.get("request_id", 0)) + int(payload.get("phase", 0)) * 1000003
        experts = weighted_experts(weights, int(payload.get("top_k", TOP_K)), seed)
        results = []
        for expert in experts:
            METRICS.observe("/route_expert", "200", 0.0, expert=expert)
            url = EXPERT_BASE_URL.format(id=expert)
            results.append(post_json(f"{url}/infer", {**payload, "expert": expert}))
        return post_json(f"{AGGREGATOR_URL}/aggregate", {**payload, "expert_results": results})

    def handle_expert(self, payload: dict[str, Any]) -> dict[str, Any]:
        delay = float(payload.get("compute_delay_ms", EXPERT_DELAY_MS))
        sleep_ms(delay)
        payload_bytes = int(payload.get("payload_bytes", PAYLOAD_BYTES))
        METRICS.observe("/infer_expert", "200", delay, payload_bytes, expert=EXPERT_ID)
        return {
            "expert": EXPERT_ID,
            "score": (int(payload.get("tokens", 1)) + EXPERT_ID) % 997,
            "payload": "x" * max(0, payload_bytes),
        }

    def handle_aggregator(self, payload: dict[str, Any]) -> dict[str, Any]:
        sleep_ms(COMPUTE_DELAY_MS)
        request_id = int(payload.get("request_id", 0))
        cache_key_space = max(1, int(payload.get("cache_key_space", CACHE_KEY_SPACE)))
        cache_key = str(payload.get("cache_key", f"prompt-{request_id % cache_key_space}"))
        result = {
            "experts": [item.get("expert") for item in payload.get("expert_results", [])],
            "bytes": sum(len(str(item.get("payload", ""))) for item in payload.get("expert_results", [])),
        }
        post_json(f"{CACHE_URL}/put", {"key": cache_key, "value": result})
        return result

    def handle_cache(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = str(payload.get("key", ""))
        if self.path == "/put":
            CACHE[key] = payload.get("value")
            return {"ok": True, "cache_size": len(CACHE)}
        value = CACHE.get(key)
        return {"ok": True, "hit": key in CACHE, "value": value}


def main() -> None:
    server = ThreadingHTTPServer(("", PORT), Handler)
    print(f"starting {SERVICE_NAME} role={ROLE} port={PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
