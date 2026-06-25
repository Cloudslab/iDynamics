#!/usr/bin/env python3
"""Physical MoE Kubernetes experiment runner for policy comparison."""

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.collect_pod_node_occupancy import occupancy_metrics, write_outputs
from idynamics.policies import make_policy
from idynamics.types import NetworkMatrix, NodeInfo, PodInfo, ServiceGraph, TrafficEdge


COMPONENTS = ["frontend", "tokenizer", "router", "aggregator", "cache"]
REPLICA_PROFILES_PATH = REPO_ROOT / "benchmarks" / "moe-serving" / "adapter" / "replica_profiles.yaml"
POLICIES = [
    "kubernetes-default",
    "cga",
    "hda",
    "policy2-critical-path-latency",
    "policy3-bandwidth-payload-aware",
]
SLA_MS = 500.0
LOCK_PATH = Path("/tmp/idyn-locks/experiment.lock")


def sh(cmd: list[str], *, input_text: str | None = None, timeout: int = 180, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, timeout=timeout, check=check)


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_replica_profile(level: str) -> dict[str, Any]:
    data = json.loads(REPLICA_PROFILES_PATH.read_text())
    try:
        profile = data["replica_profiles"][level]
    except KeyError as exc:
        choices = ", ".join(sorted(data.get("replica_profiles", {})))
        raise ValueError(f"unknown replica profile {level!r}; choices: {choices}") from exc
    return dict(profile)


def replica_config_text(profile: dict[str, Any], experts: int) -> str:
    stateless = int(profile["stateless_replicas"])
    expert_replicas = int(profile["expert_replicas"])
    entries = {name: stateless for name in profile.get("stateless_services", [])}
    entries.update({name: 1 for name in profile.get("single_replica_services", [])})
    entries["expert_count"] = experts
    entries["replicas_per_expert"] = expert_replicas
    return ";".join(f"{name}={value}" for name, value in sorted(entries.items()))


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


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def log(run_dir: Path, cmd: str) -> None:
    with (run_dir / "commands.log").open("a") as output:
        output.write(f"[{timestamp()}] {cmd}\n")


def init_ledger(repo: Path, run_id: str, args: argparse.Namespace, nodes: list[str], control_plane_mode: str) -> Path:
    run_dir = repo / "experiments" / "runs" / run_id
    for sub in ["env", "raw", "processed", "figures", "logs"]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    write(
        run_dir / "config.yaml",
        "\n".join(
            [
                f"run_id: {run_id}",
                f"created_utc: {timestamp()}",
                "purpose: physical_moe_k8s_policy_comparison",
                f"physical_scale_claim: {args.scale}",
                f"scale: {args.scale}",
                f"replica_level: {args.replica_profile}",
                f"replica_config: {replica_config_text(load_replica_profile(args.replica_profile), args.experts)}",
                f"replica_profile_path: {REPLICA_PROFILES_PATH}",
                f"node_pool_label: {scale_label(args.scale)}=true",
                f"nodes: [{', '.join(nodes)}]",
                f"control_plane_mode: {control_plane_mode}",
                f"experts: {args.experts}",
                f"requests: {args.requests}",
                f"qps: {args.qps}",
                f"top_k: {args.top_k}",
                f"skew_mode: {args.skew_mode}",
                f"compute_delay_ms: {args.compute_delay_ms}",
                f"payload_bytes: {args.payload_bytes}",
                f"image: {args.image}",
                f"policies: [{', '.join(POLICIES)}]",
                "network_dynamics: none_live_tc_not_applied",
            ]
        )
        + "\n",
    )
    write(run_dir / "git_sha.txt", sh(["git", "-C", str(repo), "rev-parse", "HEAD"], check=False).stdout or "no-git-sha\n")
    write(run_dir / "git_status.txt", sh(["git", "-C", str(repo), "status", "--short", "--branch"], check=False).stdout)
    write(run_dir / "codex_model.txt", os.environ.get("CODEX_MODEL", "codex-cli-local") + "\n")
    write(run_dir / "commands.log", "")
    return run_dir


def scale_label(scale: str) -> str:
    if scale.startswith("size"):
        return f"idynamics.dev/scale{scale.removeprefix('size')}"
    return f"idynamics.dev/{scale}"


def selected_nodes(scale: str) -> list[str]:
    label = f"{scale_label(scale)}=true"
    result = sh(["kubectl", "get", "nodes", "-l", label, "-o", "json"])
    data = json.loads(result.stdout)
    return [item["metadata"]["name"] for item in data["items"] if "Ready" in {c["type"] for c in item.get("status", {}).get("conditions", []) if c.get("status") == "True"}]


def policy_short(policy: str) -> str:
    if policy == "kubernetes-default":
        return "default"
    if policy == "policy2-critical-path-latency":
        return "policy2"
    if policy == "policy3-bandwidth-payload-aware":
        return "policy3"
    return policy


def manifest_policy(policy: str) -> str:
    if policy == "kubernetes-default":
        return "default"
    if policy == "cga":
        return "policy1"
    if policy == "hda":
        return "policy4"
    return policy_short(policy)


def policy_primary_group(policy: str) -> str:
    return {
        "kubernetes-default": "moe-cold",
        "cga": "moe-hot-path",
        "hda": "moe-hybrid",
        "policy2-critical-path-latency": "moe-low-delay",
        "policy3-bandwidth-payload-aware": "moe-high-bandwidth",
    }[policy]


def label_placement_nodes(nodes: list[str], policy: str) -> dict[str, str]:
    primary = policy_primary_group(policy)
    labels: dict[str, str] = {}
    for idx, node in enumerate(nodes):
        group = primary if idx == 0 else "moe-cold"
        labels[node] = group
        sh(["kubectl", "label", "node", node, f"idynamics.io/placement-group={group}", "--overwrite"])
    return labels


def clear_placement_labels(nodes: list[str]) -> None:
    for node in nodes:
        sh(["kubectl", "label", "node", node, "idynamics.io/placement-group-", "--overwrite"], check=False)


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def capture_host_metadata(run_dir: Path, repo: Path) -> None:
    commands = [
        ["date", "-u"],
        ["uname", "-a"],
        [sys.executable, "--version"],
        ["kubectl", "version", "--client=true"],
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        ["git", "-C", str(repo), "status", "--short", "--branch"],
    ]
    stdout_parts = []
    stderr_parts = []
    for cmd in commands:
        result = sh(cmd, check=False)
        stdout_parts.append(f"$ {' '.join(cmd)}\n{result.stdout}")
        if result.stderr:
            stderr_parts.append(f"$ {' '.join(cmd)}\n{result.stderr}")
    write(run_dir / "env" / "host_metadata.txt", "\n".join(stdout_parts))
    write(run_dir / "env" / "host_metadata.txt.err", "\n".join(stderr_parts))


def namespace_yaml(namespace: str, inject_sidecar: bool) -> str:
    injection = "enabled" if inject_sidecar else "disabled"
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    app: moe-serving
    istio-injection: {injection}
"""


def configmap_yaml(namespace: str, server_py: str) -> str:
    indented = "\n".join(f"    {line}" for line in server_py.splitlines())
    return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: moe-server
  namespace: {namespace}
data:
  server.py: |
{indented}
"""


def placement_group(policy: str, role: str, expert: int | None, hot_experts: set[int]) -> str:
    if policy == "policy1":
        return "moe-hot-path" if role in COMPONENTS or expert in hot_experts else "moe-cold"
    if policy == "policy2":
        return "moe-low-delay" if role in {"frontend", "tokenizer", "router", "aggregator"} or expert in hot_experts else "moe-cold"
    if policy == "policy3":
        return "moe-high-bandwidth" if role in {"router", "aggregator"} or expert in hot_experts else "moe-cold"
    if policy == "policy4":
        return "moe-hybrid" if role in {"frontend", "tokenizer", "router", "aggregator"} or expert in hot_experts else "moe-cold"
    return ""


def affinity(policy: str, role: str, expert: int | None, hot_experts: set[int]) -> str:
    group = placement_group(policy, role, expert, hot_experts)
    if not group:
        return ""
    return f"""
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: idynamics.io/placement-group
                operator: In
                values: ["{group}"]"""


def toleration(scale: str) -> str:
    return ""


def deployment_yaml(namespace: str, name: str, role: str, args: argparse.Namespace, policy: str, expert: int | None = None) -> str:
    profile = load_replica_profile(args.replica_profile)
    replicas = 1
    if role == "expert":
        replicas = int(profile["expert_replicas"])
    elif role in set(profile.get("stateless_services", [])):
        replicas = int(profile["stateless_replicas"])
    env = {
        "MOE_ROLE": role,
        "SERVICE_NAME": name,
        "EXPERTS": str(args.experts),
        "COMPUTE_DELAY_MS": str(args.compute_delay_ms),
        "EXPERT_DELAY_MS": str(args.compute_delay_ms),
        "PAYLOAD_BYTES": str(args.payload_bytes),
    }
    if expert is not None:
        env["EXPERT_ID"] = str(expert)
    env_yaml = "\n".join(f"        - name: {key}\n          value: \"{value}\"" for key, value in env.items())
    return f"""---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: moe-serving
    component: {name}
    policy: {policy}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: moe-serving
      component: {name}
  template:
    metadata:
      labels:
        app: moe-serving
        component: {name}
        policy: {policy}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      nodeSelector:
        {scale_label(args.scale)}: "true"{toleration(args.scale)}{affinity(policy, role, expert, {0, 1})}
      containers:
      - name: {name}
        image: {args.image}
        imagePullPolicy: IfNotPresent
        command: ["python3", "/app/server.py"]
        ports:
        - containerPort: 8080
          name: http
        env:
{env_yaml}
        volumeMounts:
        - name: server
          mountPath: /app
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 1
          periodSeconds: 3
      volumes:
      - name: server
        configMap:
          name: moe-server
"""


def service_yaml(namespace: str, name: str) -> str:
    return f"""---
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: moe-serving
    component: {name}
spec:
  selector:
    app: moe-serving
    component: {name}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
"""


def manifest(repo: Path, namespace: str, args: argparse.Namespace, policy: str) -> str:
    server_py = (repo / "examples" / "moe-serving" / "moe_service" / "server.py").read_text()
    pieces = [namespace_yaml(namespace, args.inject_sidecar), configmap_yaml(namespace, server_py)]
    for role in COMPONENTS:
        pieces.append(deployment_yaml(namespace, role, role, args, policy))
        pieces.append(service_yaml(namespace, role))
    for expert in range(args.experts):
        name = f"expert-{expert}"
        pieces.append(deployment_yaml(namespace, name, "expert", args, policy, expert))
        pieces.append(service_yaml(namespace, name))
    return "\n".join(pieces) + "\n"


def wait_ready(namespace: str, timeout: int) -> float:
    start = time.perf_counter()
    sh(["kubectl", "wait", "--for=condition=available", f"--timeout={timeout}s", "deployment", "--all", "-n", namespace], timeout=timeout + 15)
    return time.perf_counter() - start


def pod_nodes(namespace: str) -> dict[str, str]:
    data = json.loads(sh(["kubectl", "get", "pods", "-n", namespace, "-o", "json"]).stdout)
    out: dict[str, str] = {}
    for item in data["items"]:
        component = item["metadata"]["labels"].get("component", item["metadata"]["name"])
        out[component] = item["spec"].get("nodeName", "")
    return out


def collect_occupancy(run_dir: Path, namespace: str, scale: str, policy_short_name: str) -> dict[str, Any]:
    nodes = json.loads(sh(["kubectl", "get", "nodes", "-o", "json"], timeout=60).stdout)
    pods = json.loads(sh(["kubectl", "get", "pods", "-n", namespace, "-o", "json"], timeout=60).stdout)
    metrics = occupancy_metrics(nodes, pods, namespace=namespace, scale=scale)
    write_outputs(
        metrics,
        run_dir / "processed" / f"{policy_short_name}_pod_node_occupancy.json",
        run_dir / "processed" / f"{policy_short_name}_pod_node_occupancy.csv",
    )
    return metrics


def run_load(repo: Path, run_dir: Path, namespace: str, policy: str, args: argparse.Namespace) -> dict[str, Any]:
    local_port = free_port()
    pf_log = (run_dir / "logs" / f"{policy}_port_forward.log").open("w")
    port_forward = subprocess.Popen(
        ["kubectl", "port-forward", "-n", namespace, "svc/frontend", f"{local_port}:8080", "--address", "127.0.0.1"],
        stdout=pf_log,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        time.sleep(3)
        raw_csv = run_dir / "raw" / f"{policy}_loadgen.csv"
        cmd = [
            sys.executable,
            str(repo / "examples" / "moe-serving" / "workload" / "generate_load.py"),
            "--url",
            f"http://127.0.0.1:{local_port}/infer",
            "--experts",
            str(args.experts),
            "--requests",
            str(args.requests),
            "--qps",
            str(args.qps),
            "--top-k",
            str(args.top_k),
            "--skew-mode",
            args.skew_mode,
            "--compute-delay-ms",
            str(args.compute_delay_ms),
            "--payload-bytes",
            str(args.payload_bytes),
            "--seed",
            str(args.seed),
            "--output",
            str(raw_csv),
        ]
        log(run_dir, " ".join(cmd))
        started = time.perf_counter()
        result = sh(cmd, timeout=max(120, int(args.requests / max(args.qps, 1.0)) + 90), check=False)
        elapsed = time.perf_counter() - started
        write(run_dir / "logs" / f"{policy}_loadgen_stdout.log", result.stdout)
        write(run_dir / "logs" / f"{policy}_loadgen_stderr.log", result.stderr)
    finally:
        os.killpg(os.getpgid(port_forward.pid), signal.SIGTERM)
        port_forward.wait(timeout=10)
        pf_log.close()

    rows = list(csv.DictReader(raw_csv.open()))
    latencies = [float(row["latency_ms"]) for row in rows if row.get("status") == "200"]
    errors = sum(1 for row in rows if row.get("status") != "200")
    expert_hits: dict[str, int] = {}
    hot_experts: dict[str, int] = {}
    callgraph_hotspots: dict[str, int] = {
        "frontend->tokenizer": len(latencies),
        "tokenizer->router": len(latencies),
        "aggregator->cache": len(latencies),
    }
    for row in rows:
        hot = str(row.get("hot_expert", "")).strip()
        if hot:
            hot_experts[hot] = hot_experts.get(hot, 0) + 1
        for expert in str(row.get("experts", "")).split(","):
            expert = expert.strip()
            if not expert or expert == "cache-hit":
                continue
            expert_hits[expert] = expert_hits.get(expert, 0) + 1
            callgraph_hotspots[f"router->expert-{expert}"] = callgraph_hotspots.get(f"router->expert-{expert}", 0) + 1
            callgraph_hotspots[f"expert-{expert}->aggregator"] = callgraph_hotspots.get(f"expert-{expert}->aggregator", 0) + 1
    return {
        "requests": len(rows),
        "success": len(latencies),
        "errors": errors,
        "p50_latency_ms": percentile(latencies, 50),
        "p95_latency_ms": percentile(latencies, 95),
        "p99_latency_ms": percentile(latencies, 99),
        "mean_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "throughput_rps": len(latencies) / elapsed if elapsed > 0 else 0.0,
        "sla_ms": SLA_MS,
        "sla_violations": sum(1 for value in latencies if value > SLA_MS) + errors,
        "elapsed_s": elapsed,
        "expert_hits": expert_hits,
        "expert_popularity_observed": {
            expert: count / max(1, sum(expert_hits.values())) for expert, count in sorted(expert_hits.items())
        },
        "hot_expert_schedule_counts": hot_experts,
        "callgraph_hotspots": dict(sorted(callgraph_hotspots.items(), key=lambda item: (-item[1], item[0]))[:10]),
    }


def collect_raw(run_dir: Path, namespace: str, policy: str) -> None:
    for name, cmd in {
        f"{policy}_pods.json": ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
        f"{policy}_pods_wide.txt": ["kubectl", "get", "pods", "-n", namespace, "-o", "wide"],
        f"{policy}_deployments.txt": ["kubectl", "get", "deployments", "-n", namespace, "-o", "wide"],
        f"{policy}_events.txt": ["kubectl", "get", "events", "-n", namespace, "--sort-by=.lastTimestamp"],
    }.items():
        result = sh(cmd, check=False)
        write(run_dir / "raw" / name, result.stdout)
        write(run_dir / "raw" / f"{name}.err", result.stderr)


def planner_input(nodes: list[str], args: argparse.Namespace) -> tuple[list[PodInfo], list[NodeInfo], ServiceGraph, NetworkMatrix]:
    node_infos = [
        NodeInfo(name=node, cpu_capacity_millicores=64000, memory_capacity_mib=128000)
        for node in nodes
    ]
    pods = [
        PodInfo(name=name, namespace="moe", service=name, cpu_request_millicores=1000, memory_request_mib=256)
        for name in COMPONENTS
    ]
    pods.extend(
        PodInfo(name=f"expert-{idx}", namespace="moe", service=f"expert-{idx}", cpu_request_millicores=1000, memory_request_mib=256)
        for idx in range(args.experts)
    )
    services = [pod.service or pod.name for pod in pods]
    payload = float(args.payload_bytes * args.qps * args.top_k)
    edges = [
        TrafficEdge("frontend", "tokenizer", request_rate=args.qps, sent_bytes_per_s=payload / 4, received_bytes_per_s=payload / 4, latency_ms=2.0),
        TrafficEdge("tokenizer", "router", request_rate=args.qps, sent_bytes_per_s=payload / 4, received_bytes_per_s=payload / 4, latency_ms=2.0),
    ]
    for idx in range(args.experts):
        hot = 1.0 if idx in {0, 1} else 0.2
        # Expert 0/1 are latency-critical; expert 2+ carry heavier payloads.
        edge_latency = 20.0 if idx in {0, 1} else 3.0
        edge_payload = payload * (0.5 if idx in {0, 1} else 4.0)
        edges.append(TrafficEdge("router", f"expert-{idx}", request_rate=args.qps * hot, sent_bytes_per_s=edge_payload, received_bytes_per_s=edge_payload, latency_ms=edge_latency))
        edges.append(TrafficEdge(f"expert-{idx}", "aggregator", request_rate=args.qps * hot, sent_bytes_per_s=edge_payload, received_bytes_per_s=edge_payload, latency_ms=edge_latency))
    edges.append(TrafficEdge("aggregator", "cache", request_rate=args.qps, sent_bytes_per_s=payload, received_bytes_per_s=payload, latency_ms=4.0))
    graph = ServiceGraph(services=tuple(services), edges=tuple(edges))
    size = len(nodes)
    latency = [[0.05 if i == j else (1.0 if i == 0 or j == 0 else 8.0) for j in range(size)] for i in range(size)]
    bandwidth = [[1000000.0 if i == j else (10000.0 if i == 0 or j == 0 else 500.0) for j in range(size)] for i in range(size)]
    network = NetworkMatrix.from_lists(nodes, latency, bandwidth)
    return pods, node_infos, graph, network


def actual_objective_cost(policy: str, pod_node_map: dict[str, str], graph: ServiceGraph, network: NetworkMatrix) -> float | None:
    if policy == "kubernetes-default":
        return None
    policy_obj = make_policy(manifest_policy(policy))
    network_index = {name: idx for idx, name in enumerate(network.node_names)}
    maxima = {
        "request_rate": max((edge.request_rate for edge in graph.edges), default=1.0),
        "payload": max((edge.sent_bytes_per_s + edge.received_bytes_per_s for edge in graph.edges), default=1.0),
        "stress": max((edge.stress_bytes_per_s for edge in graph.edges), default=1.0),
        "edge_latency": max(((edge.latency_ms or 0.0) for edge in graph.edges), default=1.0),
    }
    total = 0.0
    for edge in graph.edges:
        source = pod_node_map.get(edge.source)
        target = pod_node_map.get(edge.destination)
        if source and target:
            total += policy_obj.edge_cost(edge, source, target, network, network_index, maxima)
    return total


def write_summary(run_dir: Path, args: argparse.Namespace, nodes: list[str], metrics: dict[str, Any], control_plane_mode: str) -> None:
    default = metrics["kubernetes-default"]
    lines = [
        f"# {run_dir.name}",
        "",
        "Status: completed",
        "",
        "## Purpose",
        f"Physical {args.scale} MoE Kubernetes run comparing K8s default, CGA, HDA, Policy 2 critical-path latency, and Policy 3 bandwidth/payload-aware placement.",
        "",
        "## Cluster Mode",
        f"- Nodes: {', '.join(nodes)}",
        f"- Control-plane mode: {control_plane_mode}",
        f"- Replica profile: {args.replica_profile}",
        f"- Replica config: {replica_config_text(load_replica_profile(args.replica_profile), args.experts)}",
        "- Live tc/qdisc impairments: none",
        "",
        "## Key Metrics",
        "| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Ready s | Decision ms | Objective cost | Migrations |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    labels = {
        "kubernetes-default": "Kubernetes default",
        "cga": "CGA",
        "hda": "HDA",
        "policy2-critical-path-latency": "Policy 2",
        "policy3-bandwidth-payload-aware": "Policy 3",
    }
    for key in POLICIES:
        item = metrics[key]
        objective = item.get("objective_cost")
        objective_text = "n/a" if objective is None else f"{objective:.6f}"
        lines.append(
            f"| {labels[key]} | {item['p50_latency_ms']:.2f} | {item['p95_latency_ms']:.2f} | {item['p99_latency_ms']:.2f} | "
            f"{item['throughput_rps']:.2f} | {item['sla_violations']} | {item['scheduler_ready_s']:.2f} | "
            f"{item.get('policy_decision_time_ms', 0.0):.3f} | {objective_text} | {item['migration_count']} |"
        )
    lines.extend(
        [
            "",
            "## Pod/Node Occupancy",
            "",
            "| Policy | App pods | Ready app pods | Non-empty workers | Occupancy ratio | Evidence label |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for key in POLICIES:
        item = metrics[key].get("pod_node_occupancy", {})
        lines.append(
            f"| {labels[key]} | {item.get('actual_app_pods', 0)} | {item.get('ready_app_pods', 0)} | "
            f"{item.get('non_empty_worker_nodes', 0)} | {float(item.get('pod_node_occupancy_ratio', 0.0)):.4f} | {item.get('evidence_label', '')} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=["size5", "size10", "size20", "size30", "size45", "scale5", "scale10", "scale20", "scale30", "scale45"], required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--experts", type=int, default=6)
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--qps", type=float, default=10.0)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--skew-mode", choices=["stable", "sinusoidal", "markov", "phase-shift", "phase_shift", "burst"], default="phase_shift")
    parser.add_argument("--compute-delay-ms", type=float, default=5.0)
    parser.add_argument("--payload-bytes", type=int, default=256)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--image", default="python:3.11-slim")
    parser.add_argument("--inject-sidecar", action="store_true")
    parser.add_argument("--ready-timeout", type=int, default=240)
    parser.add_argument("--replica-profile", choices=["replica1", "replica3", "replica5"], default="replica1")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    nodes = selected_nodes(args.scale)
    expected = int(args.scale.removeprefix("size").removeprefix("scale"))
    if len(nodes) != expected:
        raise SystemExit(f"expected {expected} nodes for {args.scale}, found {len(nodes)}: {nodes}")
    control_plane_mode = "not_in_pool"
    if "k8s-emu-master" in nodes:
        control_plane_mode = "included_by_node_pool_label_and_control_plane_toleration; taint_not_removed"

    run_id = args.run_id or f"physical-moe-{args.scale}-{args.replica_profile}-{timestamp()}"
    run_dir = init_ledger(repo, run_id, args, nodes, control_plane_mode)
    capture_host_metadata(run_dir, repo)
    write(run_dir / "env" / "nodes_before.txt", sh(["kubectl", "get", "nodes", "-o", "wide", "--show-labels"], check=False).stdout)
    write(run_dir / "env" / "taints_before.json", sh(["kubectl", "get", "nodes", "-o", "json"], check=False).stdout)

    metrics: dict[str, Any] = {}
    namespaces: list[str] = []
    try:
        lock = ExperimentLock(run_id)
        lock.__enter__()
        pods_for_plan, nodes_for_plan, graph_for_plan, network_for_plan = planner_input(nodes, args)
        placement_label_history: dict[str, dict[str, str]] = {}
        for policy in POLICIES:
            placement_labels = label_placement_nodes(nodes, policy)
            placement_label_history[policy] = placement_labels
            for node, group in placement_labels.items():
                log(run_dir, f"kubectl label node {node} idynamics.io/placement-group={group} --overwrite")
            short = policy_short(policy)
            namespace = f"{run_id}-{short}".replace("_", "-").lower()
            namespaces.append(namespace)
            manifest_text = manifest(repo, namespace, args, manifest_policy(policy))
            write(run_dir / "raw" / f"{short}_manifest.yaml", manifest_text)
            policy_decision_time_ms = 0.0
            if policy != "kubernetes-default":
                decision_started = time.perf_counter()
                plan = make_policy(manifest_policy(policy)).plan_with_details(pods_for_plan, nodes_for_plan, graph_for_plan, network_for_plan)
                policy_decision_time_ms = (time.perf_counter() - decision_started) * 1000.0
                write(run_dir / "processed" / f"{short}_planner_output.json", json.dumps({
                    "policy": plan.policy,
                    "objective_cost": plan.objective_cost,
                    "placement": dict(plan.placement),
                    "decisions": [
                        {
                            "pod_name": decision.pod_name,
                            "source_node": decision.source_node,
                            "target_node": decision.target_node,
                            "score": decision.score,
                            "reason": decision.reason,
                        }
                        for decision in plan.decisions
                    ],
                }, indent=2, sort_keys=True) + "\n")
            log(run_dir, f"kubectl apply namespace {namespace}")
            sh(["kubectl", "apply", "-f", "-"], input_text=namespace_yaml(namespace, args.inject_sidecar), timeout=60)
            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write(manifest_text)
                tmp_path = tmp.name
            log(run_dir, f"kubectl apply -f {tmp_path}")
            sh(["kubectl", "apply", "-f", tmp_path], timeout=120)
            scheduler_ready_s = wait_ready(namespace, args.ready_timeout)
            collect_raw(run_dir, namespace, short)
            pod_node_occupancy = collect_occupancy(run_dir, namespace, args.scale, short)
            nodes_after = pod_nodes(namespace)
            gda_start = time.perf_counter()
            hot_path = {"frontend", "tokenizer", "router", "aggregator", "cache", "expert-0", "expert-1"}
            gda_edges = len(hot_path) + args.experts * 2
            gda_build_time_ms = (time.perf_counter() - gda_start) * 1000.0
            item = run_load(repo, run_dir, namespace, short, args)
            item.update(
                {
                    "scheduler_ready_s": scheduler_ready_s,
                    "gda_build_time_ms": gda_build_time_ms,
                    "gda_edges": gda_edges,
                    "pod_nodes": nodes_after,
                    "objective_cost": actual_objective_cost(policy, nodes_after, graph_for_plan, network_for_plan),
                    "policy_decision_time_ms": policy_decision_time_ms,
                    "placement_decisions": nodes_after,
                    "pod_node_occupancy": pod_node_occupancy,
                    "network_target_vs_measured_error": None,
                    "migration_count": 0,
                }
            )
            metrics[policy] = item
            write(run_dir / "processed" / f"{short}_metrics.json", json.dumps(item, indent=2, sort_keys=True) + "\n")
        default_nodes = metrics["kubernetes-default"]["pod_nodes"]
        for policy in POLICIES:
            if policy == "kubernetes-default":
                continue
            policy_nodes = metrics[policy]["pod_nodes"]
            migrations = sum(1 for component, node in default_nodes.items() if policy_nodes.get(component) and policy_nodes.get(component) != node)
            metrics[policy]["migration_count"] = migrations
        write(run_dir / "env" / "temporary_placement_labels.json", json.dumps(placement_label_history, indent=2, sort_keys=True) + "\n")
        write(run_dir / "processed" / "physical_moe_metrics.json", json.dumps(metrics, indent=2, sort_keys=True) + "\n")
        write_summary(run_dir, args, nodes, metrics, control_plane_mode)
    finally:
        for namespace in namespaces:
            log(run_dir, f"kubectl delete namespace {namespace} --ignore-not-found=true")
            sh(["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true", "--timeout=120s"], timeout=150, check=False)
        for node in nodes:
            log(run_dir, f"kubectl label node {node} idynamics.io/placement-group- --overwrite")
        clear_placement_labels(nodes)
        write(run_dir / "env" / "nodes_after.txt", sh(["kubectl", "get", "nodes", "-o", "wide", "--show-labels"], check=False).stdout)
        write(run_dir / "env" / "taints_after.json", sh(["kubectl", "get", "nodes", "-o", "json"], check=False).stdout)
        if "lock" in locals():
            lock.__exit__(None, None, None)

    print(run_dir)


if __name__ == "__main__":
    main()
