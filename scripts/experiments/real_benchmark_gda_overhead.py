#!/usr/bin/env python3
"""Ledger-backed live benchmark overhead evaluation for GDA Algorithm 1.

The runner deploys one real upstream benchmark, generates a bounded HTTP
workload, reconstructs the active call graph from Istio Prometheus telemetry,
and records sparse graph-construction overhead together with the logical dense
pairwise query baseline. Failed upstream deployments are kept as explicit
blocked ledgers so reported results can distinguish measured rows from attempts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from idynamics.gda.sparse import build_graph_from_traffic_edges, legacy_dense_query_count, sparse_query_count
from idynamics.types import TrafficEdge
from scripts.evaluation.collect_pod_node_occupancy import occupancy_metrics, write_outputs


RUNS_DIR = REPO_ROOT / "experiments" / "runs"
LOCK_PATH = Path("/tmp/idyn-locks/experiment.lock")
SCALE_CHOICES = ("scale10", "scale20", "scale30", "scale45")


@dataclass(frozen=True)
class BenchmarkSpec:
    key: str
    display_name: str
    default_scale: str
    source_root: Path
    endpoint_service: str
    endpoint_port: int
    deploy_timeout_s: int
    rollout_timeout_s: int
    load_kind: str
    expected_min_edges: int = 1


BENCHMARKS: dict[str, BenchmarkSpec] = {
    "online-boutique": BenchmarkSpec(
        key="online-boutique",
        display_name="Online Boutique / Google Microservices Demo",
        default_scale="scale45",
        source_root=Path("/home/ubuntu/idyn-external/online-boutique"),
        endpoint_service="frontend",
        endpoint_port=80,
        deploy_timeout_s=300,
        rollout_timeout_s=480,
        load_kind="online_boutique",
        expected_min_edges=3,
    ),
    "social-network": BenchmarkSpec(
        key="social-network",
        display_name="DeathStarBench Social Network",
        default_scale="scale45",
        source_root=Path("/home/ubuntu/idyn-external/deathstarbench/socialNetwork"),
        endpoint_service="nginx-thrift",
        endpoint_port=8080,
        deploy_timeout_s=480,
        rollout_timeout_s=600,
        load_kind="social_network",
        expected_min_edges=3,
    ),
    "train-ticket": BenchmarkSpec(
        key="train-ticket",
        display_name="Train Ticket",
        default_scale="scale45",
        source_root=Path("/home/ubuntu/idyn-external/train-ticket"),
        endpoint_service="ts-ui-dashboard",
        endpoint_port=8080,
        deploy_timeout_s=360,
        rollout_timeout_s=900,
        load_kind="train_ticket",
        expected_min_edges=1,
    ),
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def sh(
    cmd: list[str],
    *,
    run_dir: Path | None = None,
    timeout: int = 120,
    check: bool = True,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    if run_dir is not None:
        with (run_dir / "commands.log").open("a") as log:
            log.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, input=input_text, text=True, capture_output=True, timeout=timeout, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def capture(run_dir: Path, rel: str, cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    result = sh(cmd, run_dir=run_dir, timeout=timeout, check=False)
    write(run_dir / rel, result.stdout)
    if result.stderr:
        write(run_dir / f"{rel}.err", result.stderr)
    return result


class ExperimentLock:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    def __enter__(self) -> None:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{self.run_id}\n{os.getpid()}\n".encode())
        os.close(fd)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass


def init_run(run_id: str, config: dict[str, Any]) -> Path:
    run_dir = RUNS_DIR / run_id
    for sub in ("env", "raw", "processed", "figures", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    write(run_dir / "commands.log", "")
    write(run_dir / "codex_model.txt", os.environ.get("CODEX_MODEL", "codex-cli-local") + "\n")
    write(run_dir / "git_sha.txt", sh(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=False).stdout or "no-git-sha\n")
    write(run_dir / "git_status.txt", sh(["git", "status", "--short", "--branch"], cwd=REPO_ROOT, check=False).stdout)
    body = {"run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(), **config}
    write(run_dir / "config.yaml", "\n".join(f"{key}: {json.dumps(value)}" for key, value in body.items()) + "\n")
    return run_dir


def capture_environment(run_dir: Path) -> None:
    captures = {
        "env/kubernetes_version.txt": ["kubectl", "version", "-o", "yaml"],
        "env/nodes_wide.txt": ["kubectl", "get", "nodes", "-o", "wide", "--show-labels"],
        "env/pods_all_namespaces_wide.txt": ["kubectl", "get", "pods", "-A", "-o", "wide"],
        "env/services_all_namespaces.txt": ["kubectl", "get", "svc", "-A"],
        "env/storageclasses.txt": ["kubectl", "get", "storageclass", "-o", "wide"],
        "env/istio_prometheus.txt": ["kubectl", "-n", "istio-system", "get", "svc,pods", "-l", "app=prometheus", "-o", "wide"],
    }
    for rel, cmd in captures.items():
        capture(run_dir, rel, cmd, timeout=90)


def verify_scale(scale: str, run_dir: Path) -> list[str]:
    label = f"idynamics.dev/{scale}=true"
    result = sh(["kubectl", "get", "nodes", "-l", label, "-o", "json"], run_dir=run_dir, timeout=90)
    data = json.loads(result.stdout)
    nodes = []
    for item in data.get("items", []):
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in item.get("status", {}).get("conditions", []))
        if ready:
            nodes.append(item["metadata"]["name"])
    expected = int(scale.removeprefix("scale"))
    if len(nodes) != expected:
        raise RuntimeError(f"{label} selected {len(nodes)} Ready nodes, expected {expected}: {nodes}")
    write(run_dir / "env" / "selected_worker_nodes.json", json.dumps(nodes, indent=2) + "\n")
    return nodes


def create_namespace(namespace: str, run_dir: Path, *, istio_injection: str = "enabled") -> None:
    ns_yaml = sh(["kubectl", "create", "namespace", namespace, "--dry-run=client", "-o", "yaml"], run_dir=run_dir).stdout
    apply = sh(["kubectl", "apply", "-f", "-"], input_text=ns_yaml, run_dir=run_dir, timeout=60, check=False)
    write(run_dir / "logs" / "namespace_apply.stdout", apply.stdout)
    write(run_dir / "logs" / "namespace_apply.stderr", apply.stderr)
    if apply.returncode != 0:
        raise RuntimeError(apply.stderr.strip())
    sh(["kubectl", "label", "namespace", namespace, f"istio-injection={istio_injection}", "--overwrite"], run_dir=run_dir, timeout=60)
    sh(["kubectl", "label", "namespace", namespace, "idynamics.dev/gda-overhead=true", "--overwrite"], run_dir=run_dir, timeout=60)


def patch_all_deployments_for_scale(run_dir: Path, namespace: str, scale: str) -> list[str]:
    result = sh(["kubectl", "-n", namespace, "get", "deploy", "-o", "json"], run_dir=run_dir, timeout=90, check=False)
    if result.returncode != 0:
        write(run_dir / "logs" / "patch_deployments.err", result.stderr)
        return []
    data = json.loads(result.stdout)
    patch = json.dumps({"spec": {"template": {"spec": {"nodeSelector": {f"idynamics.dev/{scale}": "true"}}}}})
    names = []
    for item in data.get("items", []):
        name = item["metadata"]["name"]
        names.append(name)
        sh(["kubectl", "-n", namespace, "patch", "deployment", name, "--type=merge", "-p", patch], run_dir=run_dir, timeout=60, check=False)
    write(run_dir / "processed" / "patched_deployments.json", json.dumps(names, indent=2) + "\n")
    return names


def wait_deployments_available(run_dir: Path, namespace: str, timeout_s: int) -> subprocess.CompletedProcess[str]:
    result = sh(
        ["kubectl", "-n", namespace, "wait", "--for=condition=available", "deployment", "--all", f"--timeout={timeout_s}s"],
        run_dir=run_dir,
        timeout=timeout_s + 90,
        check=False,
    )
    write(run_dir / "logs" / "rollout_wait.stdout", result.stdout)
    write(run_dir / "logs" / "rollout_wait.stderr", result.stderr)
    return result


def collect_namespace(run_dir: Path, namespace: str, prefix: str) -> None:
    captures = {
        f"raw/{prefix}_pods.json": ["kubectl", "-n", namespace, "get", "pods", "-o", "json"],
        f"raw/{prefix}_pods_wide.txt": ["kubectl", "-n", namespace, "get", "pods", "-o", "wide"],
        f"raw/{prefix}_deployments.json": ["kubectl", "-n", namespace, "get", "deploy", "-o", "json"],
        f"raw/{prefix}_deployments.txt": ["kubectl", "-n", namespace, "get", "deploy", "-o", "wide"],
        f"raw/{prefix}_services.txt": ["kubectl", "-n", namespace, "get", "svc", "-o", "wide"],
        f"raw/{prefix}_events.txt": ["kubectl", "-n", namespace, "get", "events", "--sort-by=.lastTimestamp"],
        f"raw/{prefix}_top_pods.txt": ["kubectl", "-n", namespace, "top", "pods"],
        f"raw/{prefix}_top_nodes.txt": ["kubectl", "top", "nodes"],
    }
    for rel, cmd in captures.items():
        capture(run_dir, rel, cmd, timeout=90)


def collect_occupancy(run_dir: Path, namespace: str, scale: str, prefix: str) -> dict[str, Any]:
    nodes_result = sh(["kubectl", "get", "nodes", "-o", "json"], run_dir=run_dir, timeout=90)
    pods_result = sh(["kubectl", "-n", namespace, "get", "pods", "-o", "json"], run_dir=run_dir, timeout=90)
    metrics = occupancy_metrics(json.loads(nodes_result.stdout), json.loads(pods_result.stdout), namespace=namespace, scale=scale)
    write_outputs(metrics, run_dir / "processed" / f"{prefix}_pod_node_occupancy.json", run_dir / "processed" / f"{prefix}_pod_node_occupancy.csv")
    return metrics


def service_count(namespace: str, run_dir: Path) -> int:
    result = sh(["kubectl", "-n", namespace, "get", "deploy", "-o", "json"], run_dir=run_dir, timeout=90, check=False)
    if result.returncode != 0:
        return 0
    data = json.loads(result.stdout)
    return len([item for item in data.get("items", []) if int(item.get("spec", {}).get("replicas") or 0) > 0])


def deploy_online_boutique(spec: BenchmarkSpec, namespace: str, scale: str, run_dir: Path, args: argparse.Namespace) -> None:
    manifest = spec.source_root / "release" / "kubernetes-manifests.yaml"
    istio_manifest = spec.source_root / "release" / "istio-manifests.yaml"
    if not manifest.exists():
        raise RuntimeError(f"missing Online Boutique release manifest: {manifest}")
    create_namespace(namespace, run_dir)
    capture(run_dir, "raw/upstream_online_boutique_manifest.yaml", ["cat", str(manifest)], timeout=30)
    sh(["kubectl", "-n", namespace, "apply", "-f", str(manifest)], run_dir=run_dir, timeout=spec.deploy_timeout_s)
    if istio_manifest.exists():
        sh(["kubectl", "-n", namespace, "apply", "-f", str(istio_manifest)], run_dir=run_dir, timeout=120, check=False)
    patch_all_deployments_for_scale(run_dir, namespace, scale)
    sh(
        [
            "kubectl",
            "-n",
            namespace,
            "set",
            "env",
            "deployment/loadgenerator",
            f"USERS={args.loadgenerator_users}",
            f"RATE={args.loadgenerator_rate}",
            "FRONTEND_ADDR=frontend:80",
        ],
        run_dir=run_dir,
        timeout=90,
        check=False,
    )
    ready = wait_deployments_available(run_dir, namespace, spec.rollout_timeout_s)
    if ready.returncode != 0:
        raise RuntimeError("Online Boutique deployments did not become Available; see logs/rollout_wait.stderr")


def deploy_social_network(spec: BenchmarkSpec, namespace: str, scale: str, run_dir: Path, args: argparse.Namespace) -> None:
    chart = spec.source_root / "helm-chart" / "socialnetwork"
    if not chart.exists():
        raise RuntimeError(f"missing DeathStarBench Social Network Helm chart: {chart}")
    create_namespace(namespace, run_dir)
    capture(run_dir, "raw/socialnetwork_helm_values.yaml", ["cat", str(chart / "values.yaml")], timeout=30)
    sh(["helm", "dependency", "build", str(chart)], run_dir=run_dir, timeout=300, check=False)
    release = "idyn-social"
    install = sh(
        [
            "helm",
            "upgrade",
            "--install",
            release,
            str(chart),
            "--namespace",
            namespace,
            "--create-namespace",
            "--timeout",
            f"{spec.deploy_timeout_s}s",
            "--set",
            "global.replicas=1",
            "--set",
            "global.hpa.enabled=false",
            "--set-string",
            "global.imagePullPolicy=IfNotPresent",
        ],
        run_dir=run_dir,
        timeout=spec.deploy_timeout_s + 120,
        check=False,
    )
    write(run_dir / "logs" / "helm_upgrade.stdout", install.stdout)
    write(run_dir / "logs" / "helm_upgrade.stderr", install.stderr)
    if install.returncode != 0:
        raise RuntimeError("DeathStarBench Social Network Helm install failed; see logs/helm_upgrade.stderr")
    patch_all_deployments_for_scale(run_dir, namespace, scale)
    ready = wait_deployments_available(run_dir, namespace, spec.rollout_timeout_s)
    if ready.returncode != 0:
        raise RuntimeError("DeathStarBench Social Network deployments did not become Available; see logs/rollout_wait.stderr")


def deploy_train_ticket(spec: BenchmarkSpec, namespace: str, scale: str, run_dir: Path, args: argparse.Namespace) -> None:
    manifest_dir = spec.source_root / "deployment" / "kubernetes-manifests" / "k8s-with-istio"
    if not manifest_dir.exists():
        raise RuntimeError(f"missing Train Ticket k8s-with-istio manifests: {manifest_dir}")
    create_namespace(namespace, run_dir)
    for name in ("README.md", "ts-deployment-part1.yml", "ts-deployment-part2.yml", "ts-deployment-part3.yml", "trainticket-gateway.yaml"):
        path = manifest_dir / name
        if path.exists():
            capture(run_dir, f"raw/train_ticket_{name.replace('/', '_')}", ["cat", str(path)], timeout=30)
    for manifest in ("ts-deployment-part1.yml", "ts-deployment-part2.yml", "ts-deployment-part3.yml", "trainticket-gateway.yaml"):
        sh(["kubectl", "-n", namespace, "apply", "-f", str(manifest_dir / manifest)], run_dir=run_dir, timeout=spec.deploy_timeout_s, check=False)
    patch_all_deployments_for_scale(run_dir, namespace, scale)
    ready = wait_deployments_available(run_dir, namespace, spec.rollout_timeout_s)
    if ready.returncode != 0:
        raise RuntimeError("Train Ticket deployments did not become Available; see logs/rollout_wait.stderr")


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def start_port_forward(run_dir: Path, namespace: str, target: str, local_port: int, remote_port: int) -> subprocess.Popen[str]:
    log = (run_dir / "logs" / f"port-forward-{namespace}-{target.replace('/', '-')}.log").open("w")
    cmd = ["kubectl", "-n", namespace, "port-forward", target, f"{local_port}:{remote_port}", "--address", "127.0.0.1"]
    with (run_dir / "commands.log").open("a") as commands:
        commands.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    proc = subprocess.Popen(cmd, text=True, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.time() + 30
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", local_port)) == 0:
                return proc
        if proc.poll() is not None:
            raise RuntimeError(f"port-forward exited early: {' '.join(cmd)}")
        time.sleep(0.5)
    stop_process(proc)
    raise RuntimeError(f"port-forward did not become ready: {' '.join(cmd)}")


def stop_process(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=8)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)


def http_request(base_url: str, path: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None, timeout: float = 8.0) -> dict[str, Any]:
    started = time.perf_counter()
    status = 0
    size = 0
    error = ""
    try:
        request = urllib.request.Request(base_url + path, data=body, headers=headers or {}, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            status = int(response.status)
            size = len(payload)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        try:
            size = len(exc.read())
        except Exception:
            size = 0
        error = str(exc)
    except Exception as exc:
        error = repr(exc)
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "method": method,
        "status": status,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
        "bytes": size,
        "error": error,
    }


def social_compose_body(rng: random.Random) -> bytes:
    user_id = rng.randint(0, 961)
    text = f"idynamics benchmark post {rng.randint(1, 10_000_000)}"
    params = {
        "username": f"username_{user_id}",
        "user_id": str(user_id),
        "text": text,
        "media_ids": "[]",
        "media_types": "[]",
        "post_type": "0",
    }
    return urllib.parse.urlencode(params).encode()


def train_login_body() -> bytes:
    return json.dumps(
        {
            "username": "fdse_microservice",
            "password": "111111",
            "verificationCode": "abcd",
        }
    ).encode()


def workload_request(spec: BenchmarkSpec, base_url: str, idx: int) -> dict[str, Any]:
    rng = random.Random(idx * 7919 + int(time.time()))
    if spec.load_kind == "online_boutique":
        paths = ["/", "/product/0PUK6V6EV0", "/product/2ZYFJ3GM2N", "/cart"]
        return http_request(base_url, paths[idx % len(paths)])
    if spec.load_kind == "social_network":
        selector = idx % 10
        if selector == 0:
            return http_request(
                base_url,
                "/wrk2-api/post/compose",
                method="POST",
                body=social_compose_body(rng),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=12.0,
            )
        if selector < 7:
            uid = rng.randint(0, 961)
            return http_request(base_url, f"/wrk2-api/home-timeline/read?user_id={uid}&start=0&stop=10", timeout=12.0)
        uid = rng.randint(0, 961)
        return http_request(base_url, f"/wrk2-api/user-timeline/read?user_id={uid}&start=0&stop=10", timeout=12.0)
    if spec.load_kind == "train_ticket":
        selector = idx % 6
        if selector == 0:
            return http_request(base_url, "/api/v1/users/login", method="POST", body=train_login_body(), headers={"Content-Type": "application/json"}, timeout=12.0)
        if selector in {1, 2}:
            return http_request(base_url, "/api/v1/users/hello", timeout=8.0)
        if selector == 3:
            return http_request(base_url, "/api/v1/verifycode/generate", timeout=8.0)
        return http_request(base_url, "/", timeout=8.0)
    raise AssertionError(spec.load_kind)


def run_load(run_dir: Path, namespace: str, spec: BenchmarkSpec, duration_s: int, concurrency: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    local_port = free_port()
    proc = start_port_forward(run_dir, namespace, f"svc/{spec.endpoint_service}", local_port, spec.endpoint_port)
    rows: list[dict[str, Any]] = []
    lock = threading.Lock()
    base_url = f"http://127.0.0.1:{local_port}"
    end = time.time() + duration_s
    request_counter = 0

    def worker(worker_id: int) -> None:
        nonlocal request_counter
        while time.time() < end:
            with lock:
                idx = request_counter
                request_counter += 1
            row = workload_request(spec, base_url, idx + worker_id)
            row["worker"] = worker_id
            with lock:
                rows.append(row)

    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(worker, idx) for idx in range(concurrency)]
            for future in as_completed(futures):
                future.result()
    finally:
        elapsed = time.perf_counter() - started
        stop_process(proc)

    rows.sort(key=lambda row: row["ts"])
    ok_latencies = [float(row["latency_ms"]) for row in rows if 200 <= int(row["status"]) < 500]
    hard_errors = sum(1 for row in rows if int(row["status"]) == 0 or int(row["status"]) >= 500)
    summary = {
        "requests": len(rows),
        "success_or_expected_http": len(ok_latencies),
        "hard_errors": hard_errors,
        "error_rate": hard_errors / max(1, len(rows)),
        "throughput_rps": len(rows) / max(0.001, elapsed),
        "p50_ms": percentile(ok_latencies, 50),
        "p95_ms": percentile(ok_latencies, 95),
        "p99_ms": percentile(ok_latencies, 99),
        "elapsed_s": elapsed,
    }
    return rows, summary


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return float(ordered[index])


def prometheus_query(base_url: str, query: str) -> tuple[list[dict[str, Any]], float]:
    started = time.perf_counter()
    params = urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(f"{base_url}/api/v1/query?{params}", timeout=30) as response:
        payload = json.loads(response.read().decode())
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if payload.get("status") != "success":
        raise RuntimeError(json.dumps(payload))
    return payload["data"]["result"], elapsed_ms


def build_byte_queries(namespace: str, window: str) -> tuple[str, str]:
    selector = (
        f'source_workload!="unknown",'
        f'destination_workload!="unknown",'
        f'source_workload_namespace="{namespace}",'
        f'destination_workload_namespace="{namespace}"'
    )
    request_bytes = (
        "sum by (source_workload, destination_workload) "
        f"(increase(istio_request_bytes_sum{{{selector}}}[{window}]))"
    )
    response_bytes = (
        "sum by (source_workload, destination_workload) "
        f"(increase(istio_response_bytes_sum{{{selector}}}[{window}]))"
    )
    return request_bytes, response_bytes


def build_tcp_byte_queries(namespace: str, window: str) -> tuple[str, str]:
    selector = (
        f'source_workload!="unknown",'
        f'destination_workload!="unknown",'
        f'source_workload_namespace="{namespace}",'
        f'destination_workload_namespace="{namespace}"'
    )
    sent = (
        "sum by (source_workload, destination_workload) "
        f"(increase(istio_tcp_sent_bytes_total{{{selector}}}[{window}]))"
    )
    received = (
        "sum by (source_workload, destination_workload) "
        f"(increase(istio_tcp_received_bytes_total{{{selector}}}[{window}]))"
    )
    return sent, received


def build_request_count_queries(namespace: str, window: str) -> tuple[str, str]:
    selector = (
        f'source_workload!="unknown",'
        f'destination_workload!="unknown",'
        f'source_workload_namespace="{namespace}",'
        f'destination_workload_namespace="{namespace}"'
    )
    requests = (
        "sum by (source_workload, destination_workload) "
        f"(increase(istio_requests_total{{{selector}}}[{window}]))"
    )
    zero = "vector(0)"
    return requests, zero


def series_to_edges(sent_series: list[dict[str, Any]], received_series: list[dict[str, Any]], *, request_count_fallback: bool = False) -> list[TrafficEdge]:
    merged: dict[tuple[str, str], dict[str, float]] = {}

    def add(series: list[dict[str, Any]], field: str) -> None:
        for item in series:
            metric = item.get("metric", {})
            source = metric.get("source_workload")
            destination = metric.get("destination_workload")
            if not source or not destination or source == destination:
                continue
            value = item.get("value", [None, 0])[-1]
            try:
                amount = float(value)
            except (TypeError, ValueError):
                amount = 0.0
            if amount <= 0:
                continue
            merged.setdefault((source, destination), {"sent": 0.0, "received": 0.0, "requests": 0.0})[field] += amount

    if request_count_fallback:
        add(sent_series, "requests")
    else:
        add(sent_series, "sent")
        add(received_series, "received")
    edges = []
    for (source, destination), values in sorted(merged.items()):
        edges.append(
            TrafficEdge(
                source=source,
                destination=destination,
                request_rate=values["requests"],
                sent_bytes_per_s=values["sent"],
                received_bytes_per_s=values["received"],
            )
        )
    return edges


def measure_graph_build(services: list[str], edges: list[TrafficEdge]) -> tuple[float, float, float, int]:
    tracemalloc.start()
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    graph = build_graph_from_traffic_edges(services, edges)
    cpu_ms = (time.process_time() - start_cpu) * 1000.0
    wall_ms = (time.perf_counter() - start_wall) * 1000.0
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return wall_ms, cpu_ms, peak_bytes / (1024.0 * 1024.0), graph.number_of_edges()


def dense_local_pair_scan(services: list[str], edges: list[TrafficEdge]) -> tuple[float, int]:
    active = {(edge.source, edge.destination) for edge in edges}
    started = time.perf_counter()
    found = 0
    for source in services:
        for destination in services:
            if source != destination and (source, destination) in active:
                found += 1
    return (time.perf_counter() - started) * 1000.0, found


def current_services(namespace: str, run_dir: Path) -> list[str]:
    result = sh(["kubectl", "-n", namespace, "get", "deploy", "-o", "json"], run_dir=run_dir, timeout=90, check=False)
    if result.returncode != 0:
        return []
    services = []
    for item in json.loads(result.stdout).get("items", []):
        if int(item.get("spec", {}).get("replicas") or 0) > 0:
            services.append(item["metadata"]["name"])
    return sorted(services)


def collect_gda_samples(run_dir: Path, namespace: str, samples: int, sample_interval_s: float, window: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    port = free_port()
    proc = start_port_forward(run_dir, "istio-system", "svc/prometheus", port, 9090)
    base_url = f"http://127.0.0.1:{port}"
    services = current_services(namespace, run_dir)
    query_records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    try:
        for sample in range(1, samples + 1):
            request_query, response_query = build_byte_queries(namespace, window)
            metric_source = "istio_request_response_bytes"
            sent_series, sent_latency = prometheus_query(base_url, request_query)
            received_series, received_latency = prometheus_query(base_url, response_query)
            if not sent_series and not received_series:
                request_query, response_query = build_tcp_byte_queries(namespace, window)
                metric_source = "istio_tcp_bytes"
                sent_series, sent_latency = prometheus_query(base_url, request_query)
                received_series, received_latency = prometheus_query(base_url, response_query)
            if not sent_series and not received_series:
                request_query, response_query = build_request_count_queries(namespace, window)
                metric_source = "istio_requests_total_fallback"
                sent_series, sent_latency = prometheus_query(base_url, request_query)
                received_series = []
                received_latency = 0.0
            edges = series_to_edges(sent_series, received_series, request_count_fallback=metric_source.endswith("fallback"))
            build_wall_ms, build_cpu_ms, peak_mib, graph_edges = measure_graph_build(services, edges)
            dense_scan_ms, dense_found = dense_local_pair_scan(services, edges)
            m = len(services)
            density = graph_edges / (m * (m - 1)) if m > 1 else 0.0
            query_latency_ms = sent_latency + received_latency
            rows.append(
                {
                    "sample": sample,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "namespace": namespace,
                    "metric_source": metric_source,
                    "service_count": m,
                    "active_edges": graph_edges,
                    "density": density,
                    "sparse_query_count": sparse_query_count(),
                    "dense_logical_query_count": legacy_dense_query_count(m),
                    "query_reduction_ratio_vs_dense": legacy_dense_query_count(m) / max(1, sparse_query_count()),
                    "prometheus_query_latency_ms": query_latency_ms,
                    "graph_build_wall_ms": build_wall_ms,
                    "graph_build_cpu_ms": build_cpu_ms,
                    "gda_total_wall_ms": query_latency_ms + build_wall_ms,
                    "peak_python_memory_mib": peak_mib,
                    "dense_local_pair_scan_wall_ms": dense_scan_ms,
                    "dense_local_pair_scan_found_edges": dense_found,
                }
            )
            query_records.append(
                {
                    "sample": sample,
                    "metric_source": metric_source,
                    "sent_or_request_query": request_query,
                    "received_or_zero_query": response_query,
                    "sent_or_request_series_count": len(sent_series),
                    "received_series_count": len(received_series),
                    "edges": [
                        {
                            "source": edge.source,
                            "destination": edge.destination,
                            "request_rate": edge.request_rate,
                            "sent_bytes": edge.sent_bytes_per_s,
                            "received_bytes": edge.received_bytes_per_s,
                        }
                        for edge in edges
                    ],
                }
            )
            if sample < samples:
                time.sleep(sample_interval_s)
    finally:
        stop_process(proc)
    return rows, query_records


def summarize_gda_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}

    def values(key: str) -> list[float]:
        return [float(row[key]) for row in rows if row.get(key) not in ("", None)]

    first = rows[0]
    return {
        "samples": len(rows),
        "service_count": int(first["service_count"]),
        "active_edges_median": percentile(values("active_edges"), 50),
        "active_edges_max": max(values("active_edges")),
        "density_median": percentile(values("density"), 50),
        "sparse_query_count": int(first["sparse_query_count"]),
        "dense_logical_query_count": int(first["dense_logical_query_count"]),
        "query_reduction_ratio_vs_dense": float(first["query_reduction_ratio_vs_dense"]),
        "prometheus_query_latency_p50_ms": percentile(values("prometheus_query_latency_ms"), 50),
        "prometheus_query_latency_p95_ms": percentile(values("prometheus_query_latency_ms"), 95),
        "graph_build_wall_p50_ms": percentile(values("graph_build_wall_ms"), 50),
        "graph_build_wall_p95_ms": percentile(values("graph_build_wall_ms"), 95),
        "graph_build_cpu_p50_ms": percentile(values("graph_build_cpu_ms"), 50),
        "graph_build_cpu_p95_ms": percentile(values("graph_build_cpu_ms"), 95),
        "gda_total_wall_p50_ms": percentile(values("gda_total_wall_ms"), 50),
        "gda_total_wall_p95_ms": percentile(values("gda_total_wall_ms"), 95),
        "peak_python_memory_p95_mib": percentile(values("peak_python_memory_mib"), 95),
        "dense_local_pair_scan_wall_p95_ms": percentile(values("dense_local_pair_scan_wall_ms"), 95),
        "metric_sources": sorted({str(row["metric_source"]) for row in rows}),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0]) if rows else [])
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def render_summary(run_id: str, spec: BenchmarkSpec, namespace: str, scale: str, status: str, data: dict[str, Any]) -> str:
    lines = [
        f"# {run_id}",
        "",
        f"Status: {status}",
        f"Benchmark: {spec.display_name}",
        f"Namespace: `{namespace}`",
        f"Scale: `{scale}`",
        "",
    ]
    if data.get("source_commit"):
        lines.append(f"Source commit: `{data['source_commit']}`")
        lines.append("")
    if data.get("load_summary"):
        load = data["load_summary"]
        lines += [
            "## Load",
            "",
            f"- Requests: {load['requests']}",
            f"- Throughput: {load['throughput_rps']:.2f} req/s",
            f"- Hard error rate: {load['error_rate']:.4f}",
            f"- p50/p95/p99 latency: {load['p50_ms']:.2f}/{load['p95_ms']:.2f}/{load['p99_ms']:.2f} ms",
            "",
        ]
    if data.get("gda_summary"):
        gda = data["gda_summary"]
        lines += [
            "## GDA Overhead",
            "",
            f"- Services: {gda['service_count']}",
            f"- Active edges median/max: {gda['active_edges_median']:.0f}/{gda['active_edges_max']:.0f}",
            f"- Median density: {gda['density_median']:.6f}",
            f"- Sparse/dense logical Prometheus queries: {gda['sparse_query_count']}/{gda['dense_logical_query_count']}",
            f"- Query reduction: {gda['query_reduction_ratio_vs_dense']:.1f}x",
            f"- GDA total p50/p95: {gda['gda_total_wall_p50_ms']:.3f}/{gda['gda_total_wall_p95_ms']:.3f} ms",
            f"- Graph-build p50/p95: {gda['graph_build_wall_p50_ms']:.3f}/{gda['graph_build_wall_p95_ms']:.3f} ms",
            f"- Peak Python memory p95: {gda['peak_python_memory_p95_mib']:.6f} MiB",
            "",
        ]
    if data.get("occupancy"):
        occ = data["occupancy"]
        lines += [
            "## Pod/Node Occupancy",
            "",
            f"- Worker nodes selected: {occ['worker_nodes_selected']}",
            f"- Actual app pods: {occ['actual_app_pods']}",
            f"- Ready app pods: {occ['ready_app_pods']}",
            f"- Non-empty worker nodes: {occ['non_empty_worker_nodes']}",
            f"- Occupancy ratio: {occ['pod_node_occupancy_ratio']:.4f}",
            f"- Evidence label: {occ['evidence_label']}",
            "",
        ]
    if data.get("blocker"):
        lines += ["## Blocker", "", data["blocker"], ""]
    lines += [
        "## Claim Boundary",
        "",
        "Use measured rows only for Algorithm 1 live benchmark overhead. Blocked rows document deployment or telemetry feasibility, not benchmark performance.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> Path:
    spec = BENCHMARKS[args.benchmark]
    scale = args.scale or spec.default_scale
    run_id = args.run_id or f"gda-real-{spec.key}-{scale}-{utc_stamp()}"
    namespace = args.namespace or run_id.lower()[:63]
    source_commit = sh(["git", "-C", str(spec.source_root), "rev-parse", "HEAD"], check=False).stdout.strip()
    run_dir = init_run(
        run_id,
        {
            "purpose": "live_real_benchmark_gda_algorithm_overhead",
            "benchmark": spec.key,
            "benchmark_display_name": spec.display_name,
            "scale": scale,
            "namespace": namespace,
            "source_root": str(spec.source_root),
            "source_commit": source_commit,
            "duration_seconds": args.duration,
            "concurrency": args.concurrency,
            "gda_samples": args.samples,
            "gda_sample_interval_seconds": args.sample_interval,
            "gda_prometheus_window": args.window,
        },
    )
    data: dict[str, Any] = {"source_commit": source_commit}
    status = "deploy_blocked"
    deployers: dict[str, Callable[[BenchmarkSpec, str, str, Path, argparse.Namespace], None]] = {
        "online-boutique": deploy_online_boutique,
        "social-network": deploy_social_network,
        "train-ticket": deploy_train_ticket,
    }
    with ExperimentLock(run_id):
        try:
            verify_scale(scale, run_dir)
            capture_environment(run_dir)
            deployers[spec.key](spec, namespace, scale, run_dir, args)
            collect_namespace(run_dir, namespace, "ready")
            data["occupancy"] = collect_occupancy(run_dir, namespace, scale, "ready")
            status = "load_blocked"
            load_rows, load_summary = run_load(run_dir, namespace, spec, args.duration, args.concurrency)
            write_csv(run_dir / "raw" / "load_requests.csv", load_rows, ["ts", "worker", "path", "method", "status", "latency_ms", "bytes", "error"])
            write(run_dir / "processed" / "load_summary.json", json.dumps(load_summary, indent=2, sort_keys=True) + "\n")
            data["load_summary"] = load_summary
            if load_summary["requests"] <= 0:
                raise RuntimeError("load generator issued no requests")
            status = "telemetry_blocked"
            time.sleep(args.post_load_settle)
            gda_rows, query_records = collect_gda_samples(run_dir, namespace, args.samples, args.sample_interval, args.window)
            write_csv(run_dir / "raw" / "gda_overhead_samples.csv", gda_rows)
            write(run_dir / "raw" / "prometheus_queries_and_edges.json", json.dumps(query_records, indent=2, sort_keys=True) + "\n")
            gda_summary = summarize_gda_rows(gda_rows)
            write(run_dir / "processed" / "gda_live_overhead_summary.json", json.dumps(gda_summary, indent=2, sort_keys=True) + "\n")
            write_csv(run_dir / "processed" / "gda_live_overhead_summary.csv", [gda_summary])
            data["gda_summary"] = gda_summary
            if not gda_summary or gda_summary["active_edges_max"] < spec.expected_min_edges:
                raise RuntimeError(f"telemetry produced too few active edges for {spec.key}: {gda_summary}")
            collect_namespace(run_dir, namespace, "after_load")
            data["occupancy"] = collect_occupancy(run_dir, namespace, scale, "after_load")
            status = "measured"
        except Exception as exc:
            data["blocker"] = str(exc)
            write(run_dir / "logs" / "blocker.txt", str(exc) + "\n")
            collect_namespace(run_dir, namespace, "blocked")
        finally:
            write(run_dir / "processed" / "summary.json", json.dumps({"status": status, **data}, indent=2, sort_keys=True) + "\n")
            write(run_dir / "summary.md", render_summary(run_id, spec, namespace, scale, status, data))
            if args.cleanup:
                if spec.key == "social-network":
                    sh(["helm", "uninstall", "idyn-social", "--namespace", namespace], run_dir=run_dir, timeout=180, check=False)
                sh(["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], run_dir=run_dir, timeout=180, check=False)
    print(run_dir)
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", choices=sorted(BENCHMARKS), required=True)
    parser.add_argument("--scale", choices=SCALE_CHOICES, default="")
    parser.add_argument("--namespace", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--duration", type=int, default=45)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--sample-interval", type=float, default=3.0)
    parser.add_argument("--window", default="2m")
    parser.add_argument("--post-load-settle", type=float, default=5.0)
    parser.add_argument("--loadgenerator-users", type=int, default=10)
    parser.add_argument("--loadgenerator-rate", type=int, default=5)
    parser.add_argument("--cleanup", action="store_true")
    return parser.parse_args()


def main() -> int:
    run(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
