#!/usr/bin/env python3
"""Run an in-cluster Istio sidecar overhead benchmark.

The benchmark deploys a Fortio server and client with and without sidecar
injection, runs repeated HTTP load tests, and records latency/throughput plus
Prometheus cAdvisor CPU and memory samples for app, client, and sidecar
containers.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "experiments" / "runs"
LOCK_PATH = Path("/tmp/idyn-locks/experiment.lock")
PROM_URL = "http://127.0.0.1:19090"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sh(cmd: list[str], run_dir: Path | None = None, input_text: str | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    if run_dir is not None:
        with (run_dir / "commands.log").open("a") as log:
            log.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, input=input_text, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@contextmanager
def experiment_lock(run_id: str):
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, f"{run_id}\n{os.getpid()}\n".encode())
        os.close(fd)
        yield
    finally:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass


def init_run(args: argparse.Namespace, run_id: str) -> Path:
    run_dir = RUNS_DIR / run_id
    for sub in ["raw", "processed", "figures", "env", "logs"]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    write(run_dir / "codex_model.txt", os.environ.get("CODEX_MODEL", "codex-cli-local") + "\n")
    write(run_dir / "commands.log", "")
    write(run_dir / "git_sha.txt", sh(["git", "rev-parse", "HEAD"], timeout=20).stdout)
    write(run_dir / "git_status.txt", sh(["git", "status", "--short"], timeout=20).stdout)
    config = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "fortio two-service no-sidecar vs istio-sidecar overhead",
        "image": args.image,
        "scales": args.scales,
        "repetitions": args.repetitions,
        "qps": args.qps,
        "connections": args.connections,
        "duration": args.duration,
        "payload_bytes": args.payload_bytes,
        "node_selector_prefix": "idynamics.dev/",
        "worker_only": True,
        "prometheus": PROM_URL,
        "notes": "Resource metrics use Prometheus cAdvisor because Kubernetes Metrics API is not installed.",
    }
    write(run_dir / "config.yaml", "\n".join(f"{k}: {json.dumps(v)}" for k, v in config.items()) + "\n")
    capture_env(run_dir)
    return run_dir


def capture_env(run_dir: Path) -> None:
    captures = {
        "env/kubernetes_version.txt": ["kubectl", "version", "-o", "yaml"],
        "env/nodes_wide.txt": ["kubectl", "get", "nodes", "-o", "wide", "--show-labels"],
        "env/pods_all_namespaces_wide.txt": ["kubectl", "get", "pods", "-A", "-o", "wide"],
        "env/services_all_namespaces.txt": ["kubectl", "get", "svc", "-A"],
        "env/istioctl_version.txt": [str(REPO_ROOT / ".tools" / "istio-1.30.0" / "bin" / "istioctl"), "version"],
        "env/istio_system_deployments.yaml": ["kubectl", "-n", "istio-system", "get", "deploy", "-o", "yaml"],
        "env/prometheus_config.yaml": ["kubectl", "-n", "istio-system", "get", "cm", "prometheus", "-o", "yaml"],
    }
    for rel, cmd in captures.items():
        result = sh(cmd, run_dir=run_dir, timeout=60, check=False)
        write(run_dir / rel, result.stdout)
        if result.stderr:
            write(run_dir / f"{rel}.err", result.stderr)


def manifest(namespace: str, inject: bool, scale: str, image: str) -> str:
    injection = "enabled" if inject else "disabled"
    scale_label = f"idynamics.dev/{scale}"
    return f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    istio-injection: {injection}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortio-server
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fortio-server
  template:
    metadata:
      labels:
        app: fortio-server
        benchmark: mesh-overhead
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "15020"
        prometheus.io/path: /stats/prometheus
    spec:
      nodeSelector:
        {scale_label}: "true"
      containers:
      - name: fortio-server
        image: {image}
        imagePullPolicy: IfNotPresent
        args: ["server", "-http-port", "8080"]
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: "1"
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: fortio-server
  namespace: {namespace}
spec:
  selector:
    app: fortio-server
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortio-client
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fortio-client
  template:
    metadata:
      labels:
        app: fortio-client
        benchmark: mesh-overhead
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "15020"
        prometheus.io/path: /stats/prometheus
    spec:
      nodeSelector:
        {scale_label}: "true"
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values: ["fortio-server"]
              topologyKey: kubernetes.io/hostname
      containers:
      - name: fortio-client
        image: {image}
        imagePullPolicy: IfNotPresent
        args: ["server", "-http-port", "8082"]
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: "1"
            memory: 512Mi
"""


def deploy_condition(run_dir: Path, namespace: str, inject: bool, scale: str, image: str) -> None:
    text = manifest(namespace, inject, scale, image)
    write(run_dir / "raw" / f"{namespace}_manifest.yaml", text)
    sh(["kubectl", "apply", "-f", "-"], run_dir=run_dir, input_text=text, timeout=90)
    sh(["kubectl", "-n", namespace, "rollout", "status", "deploy/fortio-server", "--timeout=180s"], run_dir=run_dir, timeout=210)
    sh(["kubectl", "-n", namespace, "rollout", "status", "deploy/fortio-client", "--timeout=180s"], run_dir=run_dir, timeout=210)
    time.sleep(20)
    pods = sh(["kubectl", "-n", namespace, "get", "pods", "-o", "wide"], run_dir=run_dir, timeout=30).stdout
    write(run_dir / "raw" / f"{namespace}_pods_wide.txt", pods)


def delete_namespace(run_dir: Path, namespace: str) -> None:
    sh(["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], run_dir=run_dir, timeout=60, check=False)


def start_port_forward(run_dir: Path) -> subprocess.Popen[str]:
    cmd = ["kubectl", "-n", "istio-system", "port-forward", "deploy/prometheus", "19090:9090"]
    with (run_dir / "commands.log").open("a") as log:
        log.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    out = (run_dir / "logs" / "prometheus_port_forward.log").open("w")
    proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            prometheus_query("up")
            return proc
        except Exception:
            time.sleep(1)
    proc.terminate()
    raise RuntimeError("Prometheus port-forward did not become ready")


def prometheus_query(query: str) -> list[dict[str, Any]]:
    url = f"{PROM_URL}/api/v1/query?" + urllib.parse.urlencode({"query": query})
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"Prometheus HTTP {exc.code} for query {query}: {body}") from exc
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {payload}")
    return payload["data"]["result"]


def pod_names(namespace: str) -> dict[str, str]:
    output = sh(["kubectl", "-n", namespace, "get", "pod", "-l", "benchmark=mesh-overhead", "-o", "json"], timeout=40).stdout
    data = json.loads(output)
    found = {}
    for item in data["items"]:
        labels = item["metadata"].get("labels", {})
        app = labels.get("app", "")
        found[app] = item["metadata"]["name"]
    return found


def run_fortio(run_dir: Path, namespace: str, rep: int, args: argparse.Namespace) -> dict[str, Any]:
    url = f"http://fortio-server:8080/echo?size={args.payload_bytes}"
    cmd = [
        "kubectl",
        "-n",
        namespace,
        "exec",
        "deploy/fortio-client",
        "-c",
        "fortio-client",
        "--",
        "fortio",
        "load",
        "-quiet",
        "-json",
        "-",
        "-qps",
        str(args.qps),
        "-c",
        str(args.connections),
        "-t",
        args.duration,
        url,
    ]
    result = sh(cmd, run_dir=run_dir, timeout=max(180, int(duration_seconds(args.duration)) + 120), check=False)
    write(run_dir / "raw" / f"{namespace}_rep{rep}_fortio_stdout.json", result.stdout)
    write(run_dir / "logs" / f"{namespace}_rep{rep}_fortio_stderr.log", result.stderr)
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip(), "stdout": result.stdout.strip()}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"invalid fortio json: {exc}", "stdout": result.stdout[:1000]}
    return parse_fortio(payload)


def duration_seconds(text: str) -> float:
    match = re.fullmatch(r"([0-9.]+)(ms|s|m)?", text)
    if not match:
        return 30.0
    value = float(match.group(1))
    unit = match.group(2) or "s"
    return value / 1000.0 if unit == "ms" else value * 60.0 if unit == "m" else value


def percentile_from_fortio(hist: dict[str, Any], percentile: float) -> float | None:
    points = hist.get("Percentiles") or hist.get("percentiles") or []
    for point in points:
        p = point.get("Percentile") if isinstance(point, dict) else None
        v = point.get("Value") if isinstance(point, dict) else None
        if p is None or v is None:
            continue
        if abs(float(p) - percentile) < 0.001:
            return float(v)
    previous_percent = 0.0
    for bucket in hist.get("Data", []) or []:
        current_percent = float(bucket.get("Percent", 0.0))
        if current_percent < percentile:
            previous_percent = current_percent
            continue
        start = float(bucket.get("Start", bucket.get("End", 0.0)))
        end = float(bucket.get("End", start))
        span = max(current_percent - previous_percent, 1e-9)
        position = min(max((percentile - previous_percent) / span, 0.0), 1.0)
        return start + (end - start) * position
    return None


def parse_fortio(payload: dict[str, Any]) -> dict[str, Any]:
    duration_hist = payload.get("DurationHistogram") or {}
    actual_duration_raw = float(payload.get("ActualDuration") or payload.get("actual_duration") or 0.0)
    actual_duration = actual_duration_raw / 1_000_000_000.0 if actual_duration_raw > 1_000_000 else actual_duration_raw
    retcodes = payload.get("RetCodes") or {}
    requests = sum(int(v) for v in retcodes.values()) if retcodes else int(duration_hist.get("Count") or 0)
    throughput = float(payload.get("ActualQPS") or 0.0) or (requests / actual_duration if actual_duration > 0 else None)
    return {
        "ok": True,
        "requests": requests,
        "actual_duration_s": actual_duration,
        "throughput_rps": throughput,
        "p50_ms": ms(percentile_from_fortio(duration_hist, 50.0)),
        "p95_ms": ms(percentile_from_fortio(duration_hist, 95.0)),
        "p99_ms": ms(percentile_from_fortio(duration_hist, 99.0)),
        "status_200": int(retcodes.get("200", 0)) if isinstance(retcodes, dict) else None,
    }


def ms(seconds: float | None) -> float | None:
    return None if seconds is None else seconds * 1000.0


def resource_rows(namespace: str, pods: dict[str, str]) -> list[dict[str, Any]]:
    pod_regex = "|".join(pods.values())
    cpu_query = f'sum by (pod, container) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod=~"{pod_regex}",container!~"^$|POD"}}[45s]))'
    mem_query = f'avg by (pod, container) (container_memory_working_set_bytes{{namespace="{namespace}",pod=~"{pod_regex}",container!~"^$|POD"}})'
    cpu = prometheus_query(cpu_query)
    mem = prometheus_query(mem_query)
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    role_by_pod = {pod: app.replace("fortio-", "") for app, pod in pods.items()}
    for item in cpu:
        metric = item["metric"]
        key = (metric.get("pod", ""), metric.get("container", ""))
        rows.setdefault(key, {"pod": key[0], "container": key[1], "role": role_by_pod.get(key[0], "unknown")})
        rows[key]["cpu_cores"] = float(item["value"][1])
    for item in mem:
        metric = item["metric"]
        key = (metric.get("pod", ""), metric.get("container", ""))
        rows.setdefault(key, {"pod": key[0], "container": key[1], "role": role_by_pod.get(key[0], "unknown")})
        rows[key]["memory_mib"] = float(item["value"][1]) / (1024 * 1024)
    return list(rows.values())


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        write(path, "")
        return
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]], resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("ok"):
            grouped.setdefault((row["scale"], row["condition"]), []).append(row)
    summaries = []
    for (scale, condition), items in sorted(grouped.items()):
        entry: dict[str, Any] = {"scale": scale, "condition": condition, "valid_repetitions": len(items)}
        for field in ["throughput_rps", "p50_ms", "p95_ms", "p99_ms"]:
            vals = [float(item[field]) for item in items if item.get(field) is not None]
            if vals:
                entry[f"{field}_mean"] = sum(vals) / len(vals)
                entry[f"{field}_min"] = min(vals)
                entry[f"{field}_max"] = max(vals)
        summaries.append(entry)
    for entry in summaries:
        for role in ["client", "server"]:
            for container in ["fortio-client", "fortio-server", "istio-proxy"]:
                vals = [r for r in resources if r.get("scale") == entry["scale"] and r.get("condition") == entry["condition"] and r.get("role") == role and r.get("container") == container]
                if not vals:
                    continue
                for metric in ["cpu_cores", "memory_mib"]:
                    nums = [float(v[metric]) for v in vals if v.get(metric) is not None]
                    if nums:
                        entry[f"{role}_{container}_{metric}_mean"] = sum(nums) / len(nums)
    return summaries


def markdown_summary(run_id: str, summaries: list[dict[str, Any]], args: argparse.Namespace) -> str:
    lines = [
        f"# Mesh Overhead Benchmark: `{run_id}`",
        "",
        f"- Fortio image: `{args.image}`",
        f"- Load: {args.qps} qps, {args.connections} connections, {args.duration}, payload {args.payload_bytes} bytes.",
        f"- Repetitions requested: {args.repetitions} per scale/condition.",
        f"- Scales requested: {', '.join(args.scales)}.",
        "- Resource metrics source: Prometheus cAdvisor (`kubectl top` was unavailable).",
        "",
        "| Scale | Condition | Valid reps | Throughput rps mean | p50 ms mean | p95 ms mean | p99 ms mean |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(
            f"| {row['scale']} | {row['condition']} | {row.get('valid_repetitions', 0)} | "
            f"{fmt(row.get('throughput_rps_mean'))} | {fmt(row.get('p50_ms_mean'))} | "
            f"{fmt(row.get('p95_ms_mean'))} | {fmt(row.get('p99_ms_mean'))} |"
        )
    lines.extend([
        "",
        "## Claim Boundary",
        "",
        "This run supports only the measured in-cluster Fortio two-service comparison under the recorded Kubernetes, Istio, Prometheus, CRI-O, and node-placement conditions.",
    ])
    return "\n".join(lines) + "\n"


def fmt(value: Any) -> str:
    return "" if value is None else f"{float(value):.3f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=f"mesh-overhead-{utc_stamp()}")
    parser.add_argument("--image", default="fortio/fortio:1.69.3")
    parser.add_argument("--scales", nargs="+", default=["scale5", "scale20", "scale45"])
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--qps", type=float, default=100.0)
    parser.add_argument("--connections", type=int, default=16)
    parser.add_argument("--duration", default="20s")
    parser.add_argument("--payload-bytes", type=int, default=1024)
    parser.add_argument("--keep-namespaces", action="store_true")
    args = parser.parse_args()

    run_dir = init_run(args, args.run_id)
    with experiment_lock(args.run_id):
        port_forward = start_port_forward(run_dir)
        all_rows: list[dict[str, Any]] = []
        all_resources: list[dict[str, Any]] = []
        namespaces: list[str] = []
        try:
            for scale in args.scales:
                for condition, inject in [("no-sidecar", False), ("sidecar", True)]:
                    namespace = f"idyn-mesh-{scale}-{condition}".replace("sidecar", "sc").replace("no-sc", "nosc")
                    namespaces.append(namespace)
                    deploy_condition(run_dir, namespace, inject, scale, args.image)
                    pods = pod_names(namespace)
                    for rep in range(1, args.repetitions + 1):
                        result = run_fortio(run_dir, namespace, rep, args)
                        row = {"run_id": args.run_id, "scale": scale, "condition": condition, "namespace": namespace, "rep": rep, **result}
                        all_rows.append(row)
                        time.sleep(12)
                        try:
                            for resource in resource_rows(namespace, pods):
                                all_resources.append({"run_id": args.run_id, "scale": scale, "condition": condition, "namespace": namespace, "rep": rep, **resource})
                        except Exception as exc:
                            all_resources.append({"run_id": args.run_id, "scale": scale, "condition": condition, "namespace": namespace, "rep": rep, "error": str(exc)})
            write_csv(run_dir / "raw" / "fortio_repetitions.csv", all_rows)
            write_csv(run_dir / "raw" / "container_resources.csv", all_resources)
            summaries = summarize(all_rows, all_resources)
            write_csv(run_dir / "processed" / "mesh_overhead_summary.csv", summaries)
            write(run_dir / "processed" / "mesh_overhead_summary.json", json.dumps(summaries, indent=2) + "\n")
            write(run_dir / "summary.md", markdown_summary(args.run_id, summaries, args))
        finally:
            port_forward.terminate()
            try:
                port_forward.wait(timeout=5)
            except subprocess.TimeoutExpired:
                port_forward.kill()
            if not args.keep_namespaces:
                for namespace in namespaces:
                    delete_namespace(run_dir, namespace)
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
