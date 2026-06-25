#!/usr/bin/env python3
"""Deploy benchmark applications. The Social Network path is a self-contained DeathStarBench-compatible smoke
deployment: it exposes the same frontend endpoint shapes used by the paper
workload tooling while keeping the deployment reproducible from this repo.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "experiments" / "runs"
LOCK_PATH = Path("/tmp/idyn-locks/experiment.lock")
SCALE_CHOICES = ("scale5", "scale10", "scale20", "scale30", "scale45")
SOCIAL_ENDPOINTS = (
    "/wrk2-api/post/compose",
    "/wrk2-api/home-timeline/read",
    "/wrk2-api/user-timeline/read",
)
SOCIAL_SERVICES = (
    "nginx-thrift",
    "compose-post-service",
    "home-timeline-service",
    "user-timeline-service",
    "user-service",
    "text-service",
    "unique-id-service",
    "media-service",
)
HOTEL_STATIC_PVS = ("geo-pv", "profile-pv", "rate-pv", "recommendation-pv", "reservation-pv", "user-pv")
HOTEL_STATIC_PVCS = ("geo-pvc", "profile-pvc", "rate-pvc", "recommendation-pvc", "reservation-pvc", "user-pvc")


SOCIAL_SERVER = r'''
import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROLE = os.environ.get("ROLE", "backend")
PORT = int(os.environ.get("PORT", "8080"))


def call(service, path="/internal"):
    url = f"http://{service}:8080{path}"
    with urllib.request.urlopen(url, timeout=2) as response:
        response.read()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, status=200, payload=None):
        body = json.dumps(payload or {"service": ROLE, "ok": True}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send()
            return
        if ROLE == "nginx-thrift":
            start = time.perf_counter()
            if path == "/wrk2-api/post/compose":
                for svc in ["user-service", "text-service", "unique-id-service", "media-service", "compose-post-service", "user-timeline-service", "home-timeline-service"]:
                    call(svc)
            elif path == "/wrk2-api/home-timeline/read":
                for svc in ["home-timeline-service", "post-storage-service", "user-service"]:
                    if svc == "post-storage-service":
                        time.sleep(0.003)
                    else:
                        call(svc)
            elif path == "/wrk2-api/user-timeline/read":
                for svc in ["user-timeline-service", "user-service"]:
                    call(svc)
            else:
                self._send(404, {"error": "unknown social endpoint", "path": path})
                return
            self._send(200, {"service": ROLE, "path": path, "elapsed_ms": (time.perf_counter() - start) * 1000.0})
            return
        delay_ms = float(os.environ.get("DELAY_MS", "3.0"))
        time.sleep(delay_ms / 1000.0)
        self._send(200, {"service": ROLE})


ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
'''.strip()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def sh(
    cmd: list[str],
    *,
    run_dir: Path | None = None,
    input_text: str | None = None,
    timeout: int = 120,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if run_dir is not None:
        with (run_dir / "commands.log").open("a") as log:
            log.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, input=input_text, text=True, capture_output=True, timeout=timeout, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


class ExperimentLock:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.fd: int | None = None

    def __enter__(self) -> None:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(self.fd, f"{self.run_id}\n{os.getpid()}\n".encode())
        os.close(self.fd)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass


def init_run(run_id: str, purpose: str, config: dict[str, Any]) -> Path:
    run_dir = RUNS_DIR / run_id
    for sub in ("env", "raw", "processed", "figures", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    write(run_dir / "commands.log", "")
    write(run_dir / "codex_model.txt", os.environ.get("CODEX_MODEL", "codex-cli-local") + "\n")
    write(run_dir / "git_sha.txt", sh(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=False).stdout or "no-git-sha\n")
    write(run_dir / "git_status.txt", sh(["git", "status", "--short", "--branch"], cwd=REPO_ROOT, check=False).stdout)
    body = {"run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(), "purpose": purpose, **config}
    write(run_dir / "config.yaml", "\n".join(f"{key}: {json.dumps(value)}" for key, value in body.items()) + "\n")
    capture_env(run_dir)
    return run_dir


def capture_env(run_dir: Path) -> None:
    captures = {
        "env/kubernetes_version.txt": ["kubectl", "version", "-o", "yaml"],
        "env/nodes_wide.txt": ["kubectl", "get", "nodes", "-o", "wide", "--show-labels"],
        "env/pods_all_namespaces_wide.txt": ["kubectl", "get", "pods", "-A", "-o", "wide"],
        "env/services_all_namespaces.txt": ["kubectl", "get", "svc", "-A"],
    }
    for rel, cmd in captures.items():
        result = sh(cmd, run_dir=run_dir, timeout=60, check=False)
        write(run_dir / rel, result.stdout)
        if result.stderr:
            write(run_dir / f"{rel}.err", result.stderr)


def verify_scale(scale: str, run_dir: Path) -> list[str]:
    label = f"idynamics.dev/{scale}=true"
    result = sh(["kubectl", "get", "nodes", "-l", label, "-o", "json"], run_dir=run_dir)
    data = json.loads(result.stdout)
    nodes = []
    for item in data.get("items", []):
        conditions = item.get("status", {}).get("conditions", [])
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)
        if ready:
            nodes.append(item["metadata"]["name"])
    expected = int(scale.replace("scale", ""))
    if len(nodes) != expected:
        raise RuntimeError(f"{label} selected {len(nodes)} Ready nodes, expected {expected}: {nodes}")
    return nodes


def social_manifest(namespace: str, scale: str, image: str, replicas: int) -> str:
    scale_label = f"idynamics.dev/{scale}"
    server_indented = "\n".join(f"    {line}" for line in SOCIAL_SERVER.splitlines())
    pieces = [
        f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    benchmark: social-network-smoke
    istio-injection: disabled
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: social-smoke-server
  namespace: {namespace}
data:
  server.py: |
{server_indented}
"""
    ]
    for service in SOCIAL_SERVICES:
        delay = "1.0" if service in {"unique-id-service", "user-service"} else "3.0"
        pieces.append(
            f"""---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service}
  namespace: {namespace}
  labels:
    app: social-network-smoke
    component: {service}
spec:
  replicas: {replicas if service != "nginx-thrift" else 1}
  selector:
    matchLabels:
      app: social-network-smoke
      component: {service}
  template:
    metadata:
      labels:
        app: social-network-smoke
        component: {service}
    spec:
      nodeSelector:
        {scale_label}: "true"
      containers:
      - name: server
        image: {image}
        imagePullPolicy: IfNotPresent
        command: ["python3", "/app/server.py"]
        env:
        - name: ROLE
          value: "{service}"
        - name: DELAY_MS
          value: "{delay}"
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 1
          periodSeconds: 2
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 256Mi
        volumeMounts:
        - name: server
          mountPath: /app
      volumes:
      - name: server
        configMap:
          name: social-smoke-server
---
apiVersion: v1
kind: Service
metadata:
  name: {service}
  namespace: {namespace}
  labels:
    app: social-network-smoke
    component: {service}
spec:
  selector:
    app: social-network-smoke
    component: {service}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
"""
        )
    return "\n".join(pieces)


def start_port_forward(run_dir: Path, namespace: str, local_port: int, service: str, remote_port: int) -> subprocess.Popen[str]:
    cmd = ["kubectl", "-n", namespace, "port-forward", f"svc/{service}", f"{local_port}:{remote_port}"]
    with (run_dir / "commands.log").open("a") as log:
        log.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    out = (run_dir / "logs" / f"{namespace}_{service}_port_forward.log").open("w")
    proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    deadline = time.time() + 30
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", local_port)) == 0:
                return proc
            time.sleep(0.5)
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    raise RuntimeError(f"port-forward did not become ready for {namespace}/{service}")


def stop_process(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=10)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)


def request_once(base_url: str, idx: int, timeout: float) -> dict[str, Any]:
    endpoint = SOCIAL_ENDPOINTS[idx % len(SOCIAL_ENDPOINTS)]
    started = time.perf_counter()
    status = 0
    error = ""
    size = 0
    try:
        with urllib.request.urlopen(base_url + endpoint, timeout=timeout) as response:
            payload = response.read()
            status = response.status
            size = len(payload)
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = str(exc)
    except Exception as exc:
        error = repr(exc)
    return {
        "request_id": idx,
        "endpoint": endpoint,
        "status": status,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
        "bytes": size,
        "error": error,
    }


def run_social_load(run_dir: Path, namespace: str, requests: int, concurrency: int) -> dict[str, Any]:
    proc = start_port_forward(run_dir, namespace, 18080, "nginx-thrift", 8080)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(request_once, "http://127.0.0.1:18080", idx, 10.0) for idx in range(requests)]
            for future in as_completed(futures):
                rows.append(future.result())
    finally:
        elapsed = time.perf_counter() - started
        stop_process(proc)
    rows.sort(key=lambda row: int(row["request_id"]))
    raw_path = run_dir / "raw" / f"{namespace}_loadgen.csv"
    with raw_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["request_id", "endpoint", "status", "latency_ms", "bytes", "error"])
        writer.writeheader()
        writer.writerows(rows)
    latencies = [float(row["latency_ms"]) for row in rows if int(row["status"]) == 200]
    return {
        "requests": len(rows),
        "success": len(latencies),
        "errors": len(rows) - len(latencies),
        "p50_latency_ms": percentile(latencies, 50),
        "p95_latency_ms": percentile(latencies, 95),
        "p99_latency_ms": percentile(latencies, 99),
        "mean_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "throughput_rps": len(latencies) / elapsed if elapsed > 0 else 0.0,
        "elapsed_s": elapsed,
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(len(ordered) - 1, idx))]


def collect_namespace(run_dir: Path, namespace: str, prefix: str) -> None:
    commands = {
        f"raw/{prefix}_pods.json": ["kubectl", "-n", namespace, "get", "pods", "-o", "json"],
        f"raw/{prefix}_pods_wide.txt": ["kubectl", "-n", namespace, "get", "pods", "-o", "wide"],
        f"raw/{prefix}_deployments.txt": ["kubectl", "-n", namespace, "get", "deploy", "-o", "wide"],
        f"raw/{prefix}_services.txt": ["kubectl", "-n", namespace, "get", "svc", "-o", "wide"],
        f"raw/{prefix}_events.txt": ["kubectl", "-n", namespace, "get", "events", "--sort-by=.lastTimestamp"],
    }
    for rel, cmd in commands.items():
        result = sh(cmd, run_dir=run_dir, timeout=60, check=False)
        write(run_dir / rel, result.stdout)
        if result.stderr:
            write(run_dir / f"{rel}.err", result.stderr)


def run_social(args: argparse.Namespace) -> Path:
    run_id = args.run_id or f"social-smoke-{args.scale}-{utc_stamp()}"
    run_dir = init_run(
        run_id,
        "deathstarbench_social_network_compatible_smoke",
        {
            "benchmark": "social-network-smoke",
            "scale": args.scale,
            "node_selector": f"idynamics.dev/{args.scale}=true",
            "image": args.image,
            "requests": args.requests,
            "concurrency": args.concurrency,
            "replicas_per_backend_service": args.replicas,
            "worker_only": True,
            "upstream_deathstarbench_checkout": "/tmp/idyn-dsb-inspect",
        },
    )
    with ExperimentLock(run_id):
        nodes = verify_scale(args.scale, run_dir)
        namespace = args.namespace or run_id.replace("_", "-").lower()
        manifest = social_manifest(namespace, args.scale, args.image, args.replicas)
        write(run_dir / "raw" / "social_manifest.yaml", manifest)
        try:
            sh(["kubectl", "apply", "-f", "-"], input_text=manifest, run_dir=run_dir, timeout=120)
            sh(["kubectl", "-n", namespace, "wait", "--for=condition=available", "deployment", "--all", f"--timeout={args.ready_timeout}s"], run_dir=run_dir, timeout=args.ready_timeout + 30)
            collect_namespace(run_dir, namespace, "social_ready")
            metrics = run_social_load(run_dir, namespace, args.requests, args.concurrency)
            collect_namespace(run_dir, namespace, "social_after_load")
            write(run_dir / "processed" / "social_smoke_metrics.json", json.dumps(metrics, indent=2, sort_keys=True) + "\n")
            status = "completed"
        finally:
            if not args.keep:
                sh(["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], run_dir=run_dir, timeout=60, check=False)
        summary = [
            f"# {run_id}",
            "",
            f"Status: {status}",
            "",
            "## Benchmark",
            "Self-contained DeathStarBench Social Network-compatible smoke deployment.",
            "",
            "## Placement",
            f"- Scale: {args.scale}",
            f"- Node selector: `idynamics.dev/{args.scale}=true`",
            f"- Selected Ready workers: {', '.join(nodes)}",
            "- Control-plane node was not selected.",
            "",
            "## Load",
            f"- Requests: {metrics['requests']}",
            f"- Success: {metrics['success']}",
            f"- Errors: {metrics['errors']}",
            f"- p50/p95/p99 latency: {metrics['p50_latency_ms']:.2f}/{metrics['p95_latency_ms']:.2f}/{metrics['p99_latency_ms']:.2f} ms",
            f"- Throughput: {metrics['throughput_rps']:.2f} rps",
            "",
            "## Limitations",
            "This smoke deployment validates reproducible Kubernetes placement, endpoint compatibility, workload generation, and log capture. It is not a full upstream DeathStarBench Social Network deployment with MongoDB, Redis, RabbitMQ, and OpenResty-Thrift.",
        ]
        write(run_dir / "summary.md", "\n".join(summary) + "\n")
    return run_dir


def ensure_deathstarbench_checkout(run_dir: Path) -> Path:
    checkout = Path("/tmp/idyn-dsb-inspect")
    if (checkout / "hotelReservation" / "kubernetes").is_dir():
        return checkout
    sh(["git", "clone", "--depth", "1", "https://github.com/delimitrou/DeathStarBench.git", str(checkout)], run_dir=run_dir, timeout=300)
    return checkout


def patch_all_deployments_for_scale(run_dir: Path, namespace: str, scale: str) -> None:
    data = json.loads(sh(["kubectl", "-n", namespace, "get", "deploy", "-o", "json"], run_dir=run_dir).stdout)
    patch = json.dumps({"spec": {"template": {"spec": {"nodeSelector": {f"idynamics.dev/{scale}": "true"}}}}})
    for item in data.get("items", []):
        name = item["metadata"]["name"]
        sh(["kubectl", "-n", namespace, "patch", "deploy", name, "--type=merge", "-p", patch], run_dir=run_dir, timeout=60, check=False)


def patch_hotel_binary_commands(run_dir: Path, namespace: str) -> None:
    """Patch upstream manifests for the current public Hotel image layout."""
    for name in ("frontend", "geo", "profile", "rate", "recommendation", "reservation", "search", "user"):
        patch = json.dumps(
            [
                {
                    "op": "replace",
                    "path": "/spec/template/spec/containers/0/command",
                    "value": [f"/go/bin/{name}"],
                }
            ]
        )
        sh(["kubectl", "-n", namespace, "patch", "deploy", name, "--type=json", "-p", patch], run_dir=run_dir, timeout=60, check=False)


def cleanup_hotel_static_volumes(run_dir: Path, namespace: str) -> None:
    for pvc in HOTEL_STATIC_PVCS:
        sh(["kubectl", "-n", namespace, "delete", "pvc", pvc, "--ignore-not-found=true", "--wait=false"], run_dir=run_dir, timeout=30, check=False)
    for pv in HOTEL_STATIC_PVS:
        sh(["kubectl", "delete", "pv", pv, "--ignore-not-found=true", "--wait=false"], run_dir=run_dir, timeout=30, check=False)


def run_external(args: argparse.Namespace) -> Path:
    run_id = args.run_id or f"external-hotel-{args.scale}-{utc_stamp()}"
    run_dir = init_run(
        run_id,
        "deathstarbench_hotel_reservation_feasibility",
        {
            "benchmark": "deathstarbench-hotel-reservation",
            "scale": args.scale,
            "node_selector": f"idynamics.dev/{args.scale}=true",
            "source": "https://github.com/delimitrou/DeathStarBench hotelReservation/kubernetes",
            "worker_only": True,
        },
    )
    namespace = args.namespace or run_id.replace("_", "-").lower()
    status = "blocked"
    blocker = ""
    with ExperimentLock(run_id):
        nodes = verify_scale(args.scale, run_dir)
        try:
            checkout = ensure_deathstarbench_checkout(run_dir)
            source = checkout / "hotelReservation" / "kubernetes"
            write(run_dir / "raw" / "deathstarbench_commit.txt", sh(["git", "rev-parse", "HEAD"], cwd=checkout, check=False).stdout)
            write(run_dir / "raw" / "hotel_kubernetes_files.txt", "\n".join(str(path.relative_to(source)) for path in sorted(source.rglob("*.yaml"))) + "\n")
            cleanup_hotel_static_volumes(run_dir, namespace)
            sh(["kubectl", "create", "namespace", namespace], run_dir=run_dir, timeout=60, check=False)
            sh(["kubectl", "label", "namespace", namespace, "istio-injection=disabled", "--overwrite"], run_dir=run_dir, timeout=60, check=False)
            apply = sh(["kubectl", "-n", namespace, "apply", "-Rf", str(source)], run_dir=run_dir, timeout=240, check=False)
            write(run_dir / "logs" / "hotel_apply.stdout", apply.stdout)
            write(run_dir / "logs" / "hotel_apply.stderr", apply.stderr)
            patch_all_deployments_for_scale(run_dir, namespace, args.scale)
            patch_hotel_binary_commands(run_dir, namespace)
            ready = sh(["kubectl", "-n", namespace, "wait", "--for=condition=available", "deployment", "--all", f"--timeout={args.ready_timeout}s"], run_dir=run_dir, timeout=args.ready_timeout + 60, check=False)
            write(run_dir / "logs" / "hotel_rollout.stdout", ready.stdout)
            write(run_dir / "logs" / "hotel_rollout.stderr", ready.stderr)
            collect_namespace(run_dir, namespace, "hotel")
            if apply.returncode != 0:
                blocker = "kubectl apply of upstream Hotel Reservation manifests failed; see logs/hotel_apply.stderr."
            elif ready.returncode != 0:
                blocker = "Upstream Hotel Reservation deployments did not become Ready before timeout; see raw/hotel_pods_wide.txt and logs/hotel_rollout.stderr."
            else:
                metrics = run_hotel_smoke(run_dir, namespace)
                write(run_dir / "processed" / "hotel_smoke_metrics.json", json.dumps(metrics, indent=2, sort_keys=True) + "\n")
                status = "completed"
        except Exception as exc:
            blocker = repr(exc)
            collect_namespace(run_dir, namespace, "hotel_exception")
        finally:
            if not args.keep:
                sh(["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], run_dir=run_dir, timeout=60, check=False)
                cleanup_hotel_static_volumes(run_dir, namespace)
    write_external_summary(run_dir, args, nodes, status, blocker)
    return run_dir


def run_hotel_smoke(run_dir: Path, namespace: str) -> dict[str, Any]:
    proc = start_port_forward(run_dir, namespace, 15000, "frontend", 5000)
    try:
        rows = []
        for idx in range(10):
            started = time.perf_counter()
            status = 0
            error = ""
            url = "http://127.0.0.1:15000/hotels?" + urllib.parse.urlencode({"inDate": "2015-04-09", "outDate": "2015-04-10", "lat": "37.7749", "lon": "-122.4194"})
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    response.read()
                    status = response.status
            except Exception as exc:
                error = repr(exc)
            rows.append({"request_id": idx, "status": status, "latency_ms": (time.perf_counter() - started) * 1000.0, "error": error})
        with (run_dir / "raw" / "hotel_loadgen.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["request_id", "status", "latency_ms", "error"])
            writer.writeheader()
            writer.writerows(rows)
    finally:
        stop_process(proc)
    latencies = [float(row["latency_ms"]) for row in rows if int(row["status"]) == 200]
    return {
        "requests": len(rows),
        "success": len(latencies),
        "errors": len(rows) - len(latencies),
        "p95_latency_ms": percentile(latencies, 95),
    }


def write_external_summary(run_dir: Path, args: argparse.Namespace, nodes: list[str], status: str, blocker: str) -> None:
    lines = [
        f"# {run_dir.name}",
        "",
        f"Status: {status}",
        "",
        "## Benchmark",
        "DeathStarBench Hotel Reservation upstream Kubernetes manifests.",
        "",
        "## Placement",
        f"- Scale: {args.scale}",
        f"- Node selector patched onto deployments: `idynamics.dev/{args.scale}=true`",
        f"- Selected Ready workers: {', '.join(nodes)}",
        "",
    ]
    if status == "completed":
        metrics = json.loads((run_dir / "processed" / "hotel_smoke_metrics.json").read_text())
        lines.extend(
            [
                "## Smoke Result",
                f"- Requests: {metrics['requests']}",
                f"- Success: {metrics['success']}",
                f"- Errors: {metrics['errors']}",
                f"- p95 latency: {metrics['p95_latency_ms']:.2f} ms",
            ]
        )
    else:
        lines.extend(
            [
                "## Blocker",
                blocker or "Unknown blocker; inspect raw pod status and rollout logs.",
                "",
                "## Fallback",
                "Use the completed Social Network-compatible smoke path and the MoE-serving microbenchmark evidence for application-generality claims. Do not claim successful external DeathStarBench Hotel performance from this run.",
            ]
        )
    write(run_dir / "summary.md", "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    social = sub.add_parser("social-smoke")
    social.add_argument("--scale", choices=SCALE_CHOICES, default="scale10")
    social.add_argument("--run-id", default="")
    social.add_argument("--namespace", default="")
    social.add_argument("--image", default="python:3.11-slim")
    social.add_argument("--requests", type=int, default=60)
    social.add_argument("--concurrency", type=int, default=8)
    social.add_argument("--replicas", type=int, default=1)
    social.add_argument("--ready-timeout", type=int, default=240)
    social.add_argument("--keep", action="store_true")

    external = sub.add_parser("external-benchmark")
    external.add_argument("--scale", choices=SCALE_CHOICES, default="scale10")
    external.add_argument("--run-id", default="")
    external.add_argument("--namespace", default="")
    external.add_argument("--ready-timeout", type=int, default=360)
    external.add_argument("--keep", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "social-smoke":
        run_dir = run_social(args)
    elif args.command == "external-benchmark":
        run_dir = run_external(args)
    else:
        raise AssertionError(args.command)
    print(run_dir)


if __name__ == "__main__":
    main()
