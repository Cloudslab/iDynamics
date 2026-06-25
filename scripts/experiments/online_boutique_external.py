#!/usr/bin/env python3
"""Run ledger-backed Online Boutique external benchmark smoke/load tests."""

from __future__ import annotations

import argparse
import csv
import json
import os
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.collect_pod_node_occupancy import occupancy_metrics, write_outputs

RUNS_DIR = REPO_ROOT / "experiments" / "runs"
LOCK_PATH = Path("/tmp/idyn-locks/experiment.lock")
ONLINE_ROOT = Path("/home/ubuntu/idyn-external/online-boutique")
MANIFEST = ONLINE_ROOT / "release" / "kubernetes-manifests.yaml"
ISTIO_MANIFEST = ONLINE_ROOT / "release" / "istio-manifests.yaml"
REPLICA_PROFILES_PATH = REPO_ROOT / "benchmarks" / "online-boutique" / "adapter" / "replica_profiles.yaml"
SERVICES = [
    "adservice",
    "cartservice",
    "checkoutservice",
    "currencyservice",
    "emailservice",
    "frontend",
    "loadgenerator",
    "paymentservice",
    "productcatalogservice",
    "recommendationservice",
    "shippingservice",
]


def load_replica_profile(level: str) -> dict[str, Any]:
    data = json.loads(REPLICA_PROFILES_PATH.read_text())
    try:
        profile = data["replica_profiles"][level]
    except KeyError as exc:
        choices = ", ".join(sorted(data.get("replica_profiles", {})))
        raise ValueError(f"unknown replica profile {level!r}; choices: {choices}") from exc
    return dict(profile)


def replica_config_text(profile: dict[str, Any]) -> str:
    stateless_replicas = int(profile["stateless_replicas"])
    singletons = {name: 1 for name in profile.get("single_replica_services", [])}
    scaled = {name: stateless_replicas for name in profile.get("stateless_services", [])}
    parts = [f"{name}={replicas}" for name, replicas in sorted({**scaled, **singletons}.items())]
    return ";".join(parts)


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
) -> subprocess.CompletedProcess[str]:
    if run_dir is not None:
        with (run_dir / "commands.log").open("a") as log:
            log.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
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


def capture(run_dir: Path, rel: str, cmd: list[str], timeout: int = 120) -> None:
    result = sh(cmd, run_dir=run_dir, timeout=timeout, check=False)
    write(run_dir / rel, result.stdout)
    if result.stderr:
        write(run_dir / f"{rel}.err", result.stderr)


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return int(port)


def start_port_forward(run_dir: Path, namespace: str, target: str, local_port: int, remote_port: int) -> subprocess.Popen[str]:
    log = (run_dir / "logs" / f"port-forward-{namespace}-{target.replace('/', '-')}.log").open("w")
    cmd = ["kubectl", "-n", namespace, "port-forward", target, f"{local_port}:{remote_port}", "--address", "127.0.0.1"]
    with (run_dir / "commands.log").open("a") as commands:
        commands.write(f"[{datetime.now(timezone.utc).isoformat()}] {' '.join(cmd)}\n")
    proc = subprocess.Popen(cmd, text=True, stdout=log, stderr=subprocess.STDOUT)
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{local_port}", timeout=1).read(64)
            return proc
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError(f"port-forward exited early: {' '.join(cmd)}")
            time.sleep(0.5)
    return proc


def verify_scale(scale: str, run_dir: Path) -> list[str]:
    label = f"idynamics.dev/{scale}=true"
    result = sh(["kubectl", "get", "nodes", "-l", label, "-o", "json"], run_dir=run_dir)
    data = json.loads(result.stdout)
    nodes = []
    for item in data.get("items", []):
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in item.get("status", {}).get("conditions", []))
        if ready:
            nodes.append(item["metadata"]["name"])
    expected = int(scale.removeprefix("scale"))
    if len(nodes) != expected:
        raise RuntimeError(f"{label} selected {len(nodes)} Ready nodes, expected {expected}: {nodes}")
    write(run_dir / "env" / "selected_nodes.json", json.dumps(nodes, indent=2) + "\n")
    return nodes


def deploy(namespace: str, scale: str, run_dir: Path, users: int, rate: int, replica_profile: dict[str, Any]) -> None:
    ns_yaml = sh(["kubectl", "create", "namespace", namespace, "--dry-run=client", "-o", "yaml"], run_dir=run_dir).stdout
    with (run_dir / "commands.log").open("a") as log:
        log.write(f"[{datetime.now(timezone.utc).isoformat()}] kubectl apply -f - # namespace\n")
    ns_apply = subprocess.run(["kubectl", "apply", "-f", "-"], input=ns_yaml, text=True, capture_output=True)
    write(run_dir / "logs" / "namespace_apply.stdout", ns_apply.stdout)
    write(run_dir / "logs" / "namespace_apply.stderr", ns_apply.stderr)
    if ns_apply.returncode != 0:
        raise RuntimeError(f"namespace apply failed: {ns_apply.stderr.strip()}")
    sh(["kubectl", "label", "namespace", namespace, "istio-injection=enabled", "--overwrite"], run_dir=run_dir)
    capture(run_dir, "raw/online_boutique_release_manifest.yaml", ["cat", str(MANIFEST)])
    sh(["kubectl", "-n", namespace, "apply", "-f", str(MANIFEST)], run_dir=run_dir, timeout=240)
    if ISTIO_MANIFEST.exists():
        sh(["kubectl", "-n", namespace, "apply", "-f", str(ISTIO_MANIFEST)], run_dir=run_dir, timeout=120, check=False)
    selector = json.dumps({"spec": {"template": {"spec": {"nodeSelector": {f"idynamics.dev/{scale}": "true"}}}}})
    for svc in SERVICES + ["redis-cart"]:
        sh(["kubectl", "-n", namespace, "patch", "deployment", svc, "--type=merge", "-p", selector], run_dir=run_dir, timeout=60)
    stateless_replicas = str(int(replica_profile["stateless_replicas"]))
    for svc in replica_profile.get("stateless_services", []):
        sh(["kubectl", "-n", namespace, "scale", "deployment", svc, f"--replicas={stateless_replicas}"], run_dir=run_dir, timeout=60)
    for svc in replica_profile.get("single_replica_services", []):
        sh(["kubectl", "-n", namespace, "scale", "deployment", svc, "--replicas=1"], run_dir=run_dir, timeout=60)
    for svc in replica_profile.get("client_services", []):
        sh(["kubectl", "-n", namespace, "scale", "deployment", svc, "--replicas=1"], run_dir=run_dir, timeout=60)
    sh(["kubectl", "-n", namespace, "set", "env", "deployment/loadgenerator", f"USERS={users}", f"RATE={rate}", "FRONTEND_ADDR=frontend:80"], run_dir=run_dir)
    for svc in SERVICES + ["redis-cart"]:
        sh(["kubectl", "-n", namespace, "rollout", "status", f"deployment/{svc}", "--timeout=420s"], run_dir=run_dir, timeout=450)
    wait_current_pods_ready(namespace, run_dir, timeout_seconds=240)


def collect_k8s(run_dir: Path, namespace: str, prefix: str) -> None:
    capture(run_dir, f"raw/{prefix}_pods_wide.txt", ["kubectl", "-n", namespace, "get", "pods", "-o", "wide"])
    capture(run_dir, f"raw/{prefix}_pods.json", ["kubectl", "-n", namespace, "get", "pods", "-o", "json"])
    capture(run_dir, f"raw/{prefix}_deployments.txt", ["kubectl", "-n", namespace, "get", "deploy", "-o", "wide"])
    capture(run_dir, f"raw/{prefix}_services.txt", ["kubectl", "-n", namespace, "get", "svc", "-o", "wide"])
    capture(run_dir, f"raw/{prefix}_endpoints.txt", ["kubectl", "-n", namespace, "get", "endpoints"])
    capture(run_dir, f"raw/{prefix}_events.txt", ["kubectl", "-n", namespace, "get", "events", "--sort-by=.lastTimestamp"])
    capture(run_dir, f"raw/{prefix}_top_pods.txt", ["kubectl", "-n", namespace, "top", "pods"], timeout=60)
    capture(run_dir, f"raw/{prefix}_top_nodes.txt", ["kubectl", "top", "nodes"], timeout=60)


def collect_occupancy(run_dir: Path, namespace: str, scale: str, prefix: str) -> dict[str, Any]:
    nodes = json.loads(sh(["kubectl", "get", "nodes", "-o", "json"], run_dir=run_dir, timeout=60).stdout)
    pods = json.loads(sh(["kubectl", "-n", namespace, "get", "pods", "-o", "json"], run_dir=run_dir, timeout=60).stdout)
    metrics = occupancy_metrics(
        nodes,
        pods,
        namespace=namespace,
        scale=scale,
        excluded_components={"loadgenerator"},
    )
    write_outputs(
        metrics,
        run_dir / "processed" / f"{prefix}_pod_node_occupancy.json",
        run_dir / "processed" / f"{prefix}_pod_node_occupancy.csv",
    )
    return metrics


def wait_current_pods_ready(namespace: str, run_dir: Path, timeout_seconds: int = 240) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = sh(["kubectl", "-n", namespace, "get", "pods", "-o", "json"], run_dir=run_dir, timeout=60)
        pods = json.loads(result.stdout).get("items", [])
        active = [pod for pod in pods if pod.get("metadata", {}).get("deletionTimestamp") is None]
        if active and all(
            any(cond.get("type") == "Ready" and cond.get("status") == "True" for cond in pod.get("status", {}).get("conditions", []))
            for pod in active
        ):
            return
        time.sleep(5)
    raise RuntimeError(f"pods in {namespace} did not all become Ready within {timeout_seconds}s")


def request_once(base_url: str, path: str = "/") -> tuple[float, int]:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(base_url + path, timeout=5) as response:
            response.read()
            code = response.status
    except Exception:
        code = 0
    return (time.perf_counter() - start) * 1000.0, code


def run_load(base_url: str, duration: int, concurrency: int) -> list[dict[str, Any]]:
    end = time.time() + duration
    lock = threading.Lock()
    rows: list[dict[str, Any]] = []
    paths = ["/", "/product/0PUK6V6EV0", "/cart", "/product/2ZYFJ3GM2N"]

    def worker(idx: int) -> None:
        i = 0
        while time.time() < end:
            latency_ms, code = request_once(base_url, paths[(idx + i) % len(paths)])
            with lock:
                rows.append({"ts": datetime.now(timezone.utc).isoformat(), "latency_ms": latency_ms, "status": code})
            i += 1

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker, idx) for idx in range(concurrency)]
        for future in as_completed(futures):
            future.result()
    return rows


def summarize(rows: list[dict[str, Any]], duration: int) -> dict[str, float]:
    latencies = sorted(float(r["latency_ms"]) for r in rows if int(r["status"]) and int(r["status"]) < 500)
    errors = sum(1 for r in rows if int(r["status"]) == 0 or int(r["status"]) >= 500)
    if not latencies:
        return {"requests": len(rows), "throughput_rps": 0.0, "error_rate": 1.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
    def pct(p: float) -> float:
        return statistics.quantiles(latencies, n=100, method="inclusive")[int(p) - 1]
    return {
        "requests": float(len(rows)),
        "throughput_rps": float(len(rows)) / float(duration),
        "error_rate": float(errors) / float(len(rows) or 1),
        "p50_ms": float(statistics.median(latencies)),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
    }


def prometheus_query(base_url: str, query: str) -> Any:
    params = urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(f"{base_url}/api/v1/query?{params}", timeout=20) as response:
        data = json.loads(response.read().decode())
    if data.get("status") != "success":
        raise RuntimeError(json.dumps(data))
    return data["data"]["result"]


def collect_prometheus(run_dir: Path, namespace: str) -> dict[str, Any]:
    port = free_port()
    proc = start_port_forward(run_dir, "istio-system", "svc/prometheus", port, 9090)
    base = f"http://127.0.0.1:{port}"
    try:
        queries = {
            "request_rate": f'sum(rate(istio_requests_total{{destination_workload_namespace="{namespace}"}}[2m])) by (source_workload,destination_workload,response_code)',
            "latency_bucket": f'sum(rate(istio_request_duration_milliseconds_bucket{{destination_workload_namespace="{namespace}"}}[2m])) by (source_workload,destination_workload,le)',
            "callgraph_edges": f'sum(rate(istio_requests_total{{destination_workload_namespace="{namespace}",source_workload!="unknown",destination_workload!="unknown"}}[2m])) by (source_workload,destination_workload)',
        }
        outputs = {name: prometheus_query(base, query) for name, query in queries.items()}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    write(run_dir / "raw" / "prometheus_queries.json", json.dumps(queries, indent=2) + "\n")
    write(run_dir / "raw" / "prometheus_results.json", json.dumps(outputs, indent=2) + "\n")
    edges = []
    for item in outputs["callgraph_edges"]:
        metric = item["metric"]
        value = float(item["value"][1])
        if value > 0:
            edges.append({"source": metric.get("source_workload"), "destination": metric.get("destination_workload"), "rps": value})
    write(run_dir / "processed" / "gda_callgraph_edges.csv", "source,destination,rps\n" + "\n".join(f"{e['source']},{e['destination']},{e['rps']}" for e in edges) + ("\n" if edges else ""))
    metrics = {"nodes": len(set([e["source"] for e in edges] + [e["destination"] for e in edges])), "edges": len(edges), "total_edge_rps": sum(e["rps"] for e in edges)}
    write(run_dir / "processed" / "gda_callgraph_metrics.json", json.dumps(metrics, indent=2) + "\n")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=["scale10", "scale20", "scale45"], required=True)
    parser.add_argument("--duration", type=int, default=45)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--loadgenerator-users", type=int, default=10)
    parser.add_argument("--loadgenerator-rate", type=int, default=5)
    parser.add_argument("--replica-profile", choices=["replica1", "replica3", "replica5"], default="replica1")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    replica_profile = load_replica_profile(args.replica_profile)
    replica_config = replica_config_text(replica_profile)
    run_id = f"external-online-boutique-{args.scale}-{args.replica_profile}-{utc_stamp()}"
    namespace = run_id.lower()[:63]
    run_dir = init_run(run_id, {
        "purpose": "Online Boutique external benchmark smoke/load with Istio telemetry and GDA call-graph reconstruction",
        "benchmark": "online_boutique",
        "scale": args.scale,
        "replica_level": args.replica_profile,
        "replica_config": replica_config,
        "replica_profile_path": str(REPLICA_PROFILES_PATH),
        "namespace": namespace,
        "manifest": str(MANIFEST),
        "source_commit": sh(["git", "-C", str(ONLINE_ROOT), "rev-parse", "HEAD"], check=False).stdout.strip(),
        "duration_seconds": args.duration,
        "repeats": args.repeats,
        "concurrency": args.concurrency,
    })

    status = "blocked"
    summary: dict[str, Any] = {}
    with ExperimentLock(run_id):
        try:
            verify_scale(args.scale, run_dir)
            capture(run_dir, "env/kubernetes_version.txt", ["kubectl", "version", "-o", "yaml"])
            capture(run_dir, "env/nodes_wide.txt", ["kubectl", "get", "nodes", "-o", "wide", "--show-labels"])
            capture(run_dir, "env/pods_all_namespaces_wide.txt", ["kubectl", "get", "pods", "-A", "-o", "wide"])
            deploy(namespace, args.scale, run_dir, args.loadgenerator_users, args.loadgenerator_rate, replica_profile)
            collect_k8s(run_dir, namespace, "ready")
            summary["ready_occupancy"] = collect_occupancy(run_dir, namespace, args.scale, "ready")

            frontend_port = free_port()
            frontend_pf = start_port_forward(run_dir, namespace, "svc/frontend", frontend_port, 80)
            base_url = f"http://127.0.0.1:{frontend_port}"
            try:
                health_latency, health_code = request_once(base_url, "/")
                summary["endpoint_health"] = {"status": health_code, "latency_ms": health_latency}
                all_rows = []
                repeat_summaries = []
                for repeat in range(1, args.repeats + 1):
                    rows = run_load(base_url, args.duration, args.concurrency)
                    for row in rows:
                        row["repeat"] = repeat
                    all_rows.extend(rows)
                    repeat_summaries.append({"repeat": repeat, **summarize(rows, args.duration)})
                    time.sleep(5)
            finally:
                frontend_pf.terminate()
                try:
                    frontend_pf.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    frontend_pf.kill()

            with (run_dir / "raw" / "load_requests.csv").open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=["repeat", "ts", "latency_ms", "status"])
                writer.writeheader()
                writer.writerows(all_rows)
            with (run_dir / "processed" / "load_summary.csv").open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=["repeat", "requests", "throughput_rps", "error_rate", "p50_ms", "p95_ms", "p99_ms"])
                writer.writeheader()
                writer.writerows(repeat_summaries)
            summary["repeats"] = repeat_summaries
            summary["gda_callgraph"] = collect_prometheus(run_dir, namespace)
            collect_k8s(run_dir, namespace, "after_load")
            summary["after_load_occupancy"] = collect_occupancy(run_dir, namespace, args.scale, "after_load")
            occupancy_label = summary["after_load_occupancy"]["evidence_label"]
            healthy_load = all(r["error_rate"] == 0.0 and r["throughput_rps"] > 0 for r in repeat_summaries) and summary["gda_callgraph"]["edges"] > 0
            status = occupancy_label if healthy_load else "compatibility evidence"
        except Exception as exc:
            summary["error"] = str(exc)
            write(run_dir / "logs" / "failure.txt", str(exc) + "\n")
            raise
        finally:
            write(run_dir / "processed" / "summary.json", json.dumps({"status": status, **summary}, indent=2) + "\n")
            write(run_dir / "summary.md", render_summary(run_id, namespace, args.scale, args.replica_profile, replica_config, status, summary))
            if args.cleanup:
                sh(["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true"], run_dir=run_dir, timeout=240, check=False)
    print(run_dir)
    return 0


def render_summary(run_id: str, namespace: str, scale: str, replica_level: str, replica_config: str, status: str, summary: dict[str, Any]) -> str:
    lines = [f"# {run_id}", "", f"Status: {status}", "", f"Namespace: `{namespace}`", f"Scale: `{scale}`", f"Replica profile: `{replica_level}`", f"Replica config: `{replica_config}`", ""]
    if "endpoint_health" in summary:
        h = summary["endpoint_health"]
        lines.append(f"Endpoint health: HTTP {h['status']} in {h['latency_ms']:.2f} ms")
        lines.append("")
    if summary.get("repeats"):
        lines += ["## Repeated Load", "", "| Repeat | Requests | Throughput req/s | Error rate | p50 ms | p95 ms | p99 ms |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for row in summary["repeats"]:
            lines.append(f"| {row['repeat']} | {row['requests']:.0f} | {row['throughput_rps']:.2f} | {row['error_rate']:.4f} | {row['p50_ms']:.2f} | {row['p95_ms']:.2f} | {row['p99_ms']:.2f} |")
        lines.append("")
    if summary.get("gda_callgraph"):
        g = summary["gda_callgraph"]
        lines += ["## GDA Call Graph", "", f"Reconstructed `{g['nodes']}` workloads and `{g['edges']}` directed edges from Istio Prometheus telemetry.", ""]
    if summary.get("after_load_occupancy"):
        o = summary["after_load_occupancy"]
        lines += [
            "## Pod/Node Occupancy",
            "",
            f"- Worker nodes selected: {o['worker_nodes_selected']}",
            f"- Actual app pods: {o['actual_app_pods']}",
            f"- Ready app pods: {o['ready_app_pods']}",
            f"- Non-empty worker nodes: {o['non_empty_worker_nodes']}",
            f"- Occupancy ratio: {o['pod_node_occupancy_ratio']:.4f}",
            f"- Empty worker nodes: {o['empty_worker_nodes']}",
            f"- Mean app pods per non-empty node: {o['mean_app_pods_per_non_empty_node']:.2f}",
            f"- Max app pods per node: {o['max_app_pods_per_node']}",
            f"- Evidence label: {o['evidence_label']}",
            "",
        ]
    if summary.get("error"):
        lines += ["## Error", "", summary["error"], ""]
    return "\n".join(lines)



if __name__ == "__main__":
    sys.exit(main())
