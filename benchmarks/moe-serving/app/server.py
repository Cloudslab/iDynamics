#!/usr/bin/env python3
"""CPU-only MoE-style HTTP service used by the benchmark package."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROLE = os.getenv("ROLE", "frontend")
SERVICE_NAME = os.getenv("SERVICE_NAME", ROLE)
EXPERT_COUNT = max(1, int(os.getenv("EXPERT_COUNT", "4")))
CPU_WORK_MS = max(0.0, float(os.getenv("CPU_WORK_MS", "5")))
PORT = int(os.getenv("PORT", "8080"))

REQUESTS = 0
ERRORS = 0
LATENCY_MS: list[float] = []


def cpu_work(label: str, work_ms: float = CPU_WORK_MS) -> str:
    deadline = time.perf_counter() + work_ms / 1000.0
    digest = label.encode("utf-8")
    rounds = 0
    while time.perf_counter() < deadline:
        digest = hashlib.sha256(digest + rounds.to_bytes(4, "little", signed=False)).digest()
        rounds += 1
    return digest.hex()[:16]


def call(service: str, path: str, timeout: float = 2.0) -> dict[str, object]:
    url = f"http://{service}:8080{path}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parsed_query(path: str) -> dict[str, str]:
    query = urllib.parse.urlparse(path).query
    return {key: values[-1] for key, values in urllib.parse.parse_qs(query).items()}


def clamp_int(value: str | None, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        parsed = default
    return min(high, max(low, parsed))


def inference(path: str) -> dict[str, object]:
    params = parsed_query(path)
    top_k = clamp_int(params.get("top_k"), 2, 1, EXPERT_COUNT)
    payload_bytes = clamp_int(params.get("payload_bytes"), 256, 0, 8192)
    request_type = params.get("request_type", "multi_expert_top2")
    cpu_work(f"frontend:{request_type}:{payload_bytes}")
    tokenizer = call("tokenizer", f"/tokenize?payload_bytes={payload_bytes}")
    route = call("router", f"/route?top_k={top_k}&payload_bytes={payload_bytes}&request_type={request_type}")
    aggregate = call("aggregator", f"/aggregate?top_k={top_k}&request_type={request_type}")
    return {
        "service": SERVICE_NAME,
        "role": ROLE,
        "request_type": request_type,
        "top_k": top_k,
        "payload_bytes": payload_bytes,
        "tokenizer": tokenizer,
        "route": route,
        "aggregate": aggregate,
        "cpu_only": True,
    }


def role_response(path: str) -> dict[str, object]:
    params = parsed_query(path)
    if ROLE == "frontend":
        return inference(path)
    if ROLE == "tokenizer":
        payload_bytes = clamp_int(params.get("payload_bytes"), 256, 0, 8192)
        return {"role": ROLE, "tokens": max(1, payload_bytes // 16), "digest": cpu_work("tokenizer")}
    if ROLE == "router":
        top_k = clamp_int(params.get("top_k"), 2, 1, EXPERT_COUNT)
        selected = list(range(top_k))
        expert_rows = [call(f"expert-{idx}", f"/expert?expert={idx}") for idx in selected]
        return {"role": ROLE, "selected_experts": selected, "experts": expert_rows, "digest": cpu_work("router")}
    if ROLE == "expert":
        expert = params.get("expert", SERVICE_NAME.removeprefix("expert-"))
        return {"role": ROLE, "expert": expert, "digest": cpu_work(f"expert:{expert}")}
    if ROLE == "aggregator":
        cache = call("cache", "/cache")
        return {"role": ROLE, "cache": cache, "digest": cpu_work("aggregator")}
    if ROLE == "cache":
        return {"role": ROLE, "hit": True, "digest": cpu_work("cache", CPU_WORK_MS / 2.0)}
    return {"role": ROLE, "digest": cpu_work(ROLE)}


class Handler(BaseHTTPRequestHandler):
    server_version = "idynamics-moe-serving/1.0"

    def do_GET(self) -> None:  # noqa: N802
        global REQUESTS, ERRORS
        started = time.perf_counter()
        REQUESTS += 1
        try:
            if self.path.startswith("/healthz"):
                self.send_json({"ok": True, "service": SERVICE_NAME, "role": ROLE, "cpu_only": True})
            elif self.path.startswith("/metrics"):
                self.send_metrics()
            else:
                self.send_json(role_response(self.path))
        except Exception as exc:  # pragma: no cover - defensive service boundary
            ERRORS += 1
            self.send_response(500)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": exc.__class__.__name__, "message": str(exc)}).encode("utf-8"))
        finally:
            LATENCY_MS.append((time.perf_counter() - started) * 1000.0)

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def send_json(self, body: dict[str, object]) -> None:
        encoded = json.dumps(body, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_metrics(self) -> None:
        avg = sum(LATENCY_MS) / len(LATENCY_MS) if LATENCY_MS else 0.0
        body = "\n".join(
            [
                "# HELP idynamics_moe_requests_total Total HTTP requests.",
                "# TYPE idynamics_moe_requests_total counter",
                f'idynamics_moe_requests_total{{service="{SERVICE_NAME}",role="{ROLE}"}} {REQUESTS}',
                "# HELP idynamics_moe_errors_total Total request errors.",
                "# TYPE idynamics_moe_errors_total counter",
                f'idynamics_moe_errors_total{{service="{SERVICE_NAME}",role="{ROLE}"}} {ERRORS}',
                "# HELP idynamics_moe_latency_ms_avg Average handler latency in milliseconds.",
                "# TYPE idynamics_moe_latency_ms_avg gauge",
                f'idynamics_moe_latency_ms_avg{{service="{SERVICE_NAME}",role="{ROLE}"}} {avg:.6f}',
                "",
            ]
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "text/plain; version=0.0.4")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"starting {SERVICE_NAME} role={ROLE} port={PORT} cpu_only=true", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
