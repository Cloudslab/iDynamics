#!/usr/bin/env python3
"""Live tc validation and Social Network network-dynamics experiment."""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import socket
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(REPO_ROOT))

from idynamics.network.traces import BurstCorrelatedProvider, compute_network_metrics, write_frames_csv, write_metrics_json
from scripts.experiments.benchmark_deployment import (
    SOCIAL_ENDPOINTS,
    SOCIAL_SERVER,
    ExperimentLock,
    percentile,
    sh,
    start_port_forward,
    stop_process,
    utc_stamp,
    write,
)


RUNS_DIR = REPO_ROOT / "experiments" / "runs"
SCALES = ("scale10", "scale20", "scale30", "scale45")


def selected_nodes(scale: str) -> list[dict[str, str]]:
    result = sh(["kubectl", "get", "nodes", "-l", f"idynamics.dev/{scale}=true", "-o", "json"], cwd=REPO_ROOT)
    items = json.loads(result.stdout).get("items", [])
    nodes: list[dict[str, str]] = []
    for item in items:
        ready = any(
            cond.get("type") == "Ready" and cond.get("status") == "True"
            for cond in item.get("status", {}).get("conditions", [])
        )
        if not ready:
            continue
        ip = next(
            address["address"]
            for address in item.get("status", {}).get("addresses", [])
            if address.get("type") == "InternalIP"
        )
        nodes.append({"name": item["metadata"]["name"], "ip": ip})
    nodes.sort(key=lambda row: int(row["name"].split("-")[-1]) if row["name"].split("-")[-1].isdigit() else row["name"])
    expected = int(scale.replace("scale", ""))
    if len(nodes) != expected:
        raise RuntimeError(f"{scale} selected {len(nodes)} Ready workers, expected {expected}")
    return nodes


def init_run(run_id: str, purpose: str, config: dict[str, Any]) -> Path:
    run_dir = RUNS_DIR / run_id
    for sub in ("env", "raw", "processed", "figures", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    write(run_dir / "commands.log", "")
    write(run_dir / "codex_model.txt", os.environ.get("CODEX_MODEL", "codex-cli-local") + "\n")
    write(run_dir / "git_sha.txt", sh(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=False).stdout or "no-git-sha\n")
    write(run_dir / "git_status.txt", sh(["git", "status", "--short", "--branch"], cwd=REPO_ROOT, check=False).stdout)
    payload = {"run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(), "purpose": purpose, **config}
    write(run_dir / "config.yaml", "\n".join(f"{key}: {json.dumps(value)}" for key, value in payload.items()) + "\n")
    for rel, cmd in {
        "env/kubernetes_version.txt": ["kubectl", "version", "-o", "yaml"],
        "env/nodes_wide.txt": ["kubectl", "get", "nodes", "-o", "wide", "--show-labels"],
        "env/pods_all_namespaces_wide.txt": ["kubectl", "get", "pods", "-A", "-o", "wide"],
        "env/services_all_namespaces.txt": ["kubectl", "get", "svc", "-A"],
    }.items():
        result = sh(cmd, run_dir=run_dir, cwd=REPO_ROOT, check=False, timeout=80)
        write(run_dir / rel, result.stdout)
        if result.stderr:
            write(run_dir / f"{rel}.err", result.stderr)
    return run_dir


def run_logged(
    run_dir: Path,
    cmd: list[str],
    *,
    timeout: int = 120,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return sh(cmd, run_dir=run_dir, cwd=REPO_ROOT, timeout=timeout, check=check, input_text=input_text)


def snapshot(run_dir: Path, name: str, scale: str) -> None:
    out = run_dir / "env" / name
    run_logged(
        run_dir,
        [
            "env",
            f"NODE_SELECTOR=idynamics.dev/{scale}=true",
            "bash",
            "scripts/network/snapshot_qdisc_all_nodes.sh",
            str(out),
        ],
        timeout=900,
        check=False,
    )


def reset_tc(run_dir: Path, scale: str) -> None:
    run_logged(
        run_dir,
        [
            "bash",
            "scripts/network/reset_tc_all_nodes.sh",
            "--apply",
            "--selector",
            f"idynamics.dev/{scale}=true",
            "--snapshot-dir",
            str(run_dir / "env" / "qdisc_before_reset"),
        ],
        timeout=1200,
        check=False,
    )


def ssh(node: str, script: str, run_dir: Path, *, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_logged(run_dir, ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", f"ubuntu@{node}", script], timeout=timeout, check=check)


def default_iface(node: str, run_dir: Path) -> str:
    result = ssh(
        node,
        "ip route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i==\"dev\") print $(i+1)}' | head -1",
        run_dir,
    )
    iface = result.stdout.strip()
    if not iface:
        raise RuntimeError(f"could not resolve default interface on {node}")
    return iface


def apply_tc(
    nodes: list[dict[str, str]],
    run_dir: Path,
    latency_ms: float,
    bandwidth_mbps: float,
    frame: Any | None = None,
) -> None:
    """Apply egress shaping to selected worker node destinations only."""
    for src in nodes:
        iface = default_iface(src["ip"], run_dir)
        src_idx = nodes.index(src)
        lines = [
            "set -e",
            f"IFACE={iface}",
            "sudo tc qdisc replace dev \"$IFACE\" root handle 1: htb default 1",
            "sudo tc class replace dev \"$IFACE\" parent 1: classid 1:1 htb rate 10000mbit ceil 10000mbit",
        ]
        minor = 10
        for dst in nodes:
            if dst["ip"] == src["ip"]:
                continue
            dst_idx = nodes.index(dst)
            pair_latency_ms = latency_ms
            pair_bandwidth_mbps = bandwidth_mbps
            if frame is not None:
                pair_latency_ms = float(frame.latency_ms[src_idx][dst_idx])
                pair_bandwidth_mbps = float(frame.bandwidth_mbps[src_idx][dst_idx])
            handle = minor * 10
            lines.extend(
                [
                    f"sudo tc class replace dev \"$IFACE\" parent 1: classid 1:{minor} htb rate {pair_bandwidth_mbps:.1f}mbit ceil {pair_bandwidth_mbps:.1f}mbit",
                    f"sudo tc qdisc replace dev \"$IFACE\" parent 1:{minor} handle {handle}: netem delay {pair_latency_ms:.2f}ms",
                    f"sudo tc filter replace dev \"$IFACE\" protocol ip parent 1:0 prio {minor} u32 match ip dst {dst['ip']}/32 flowid 1:{minor}",
                ]
            )
            minor += 1
        ssh(src["ip"], "\n".join(lines), run_dir, timeout=180)


def ping_measure(src_ip: str, dst_ip: str, run_dir: Path, count: int = 5) -> dict[str, Any]:
    result = ssh(src_ip, f"ping -c {count} -i 0.2 -W 2 {dst_ip}", run_dir, timeout=30, check=False)
    latencies = []
    for line in result.stdout.splitlines():
        if "time=" in line:
            try:
                latencies.append(float(line.split("time=", 1)[1].split()[0]))
            except ValueError:
                pass
    return {
        "src": src_ip,
        "dst": dst_ip,
        "returncode": result.returncode,
        "samples": len(latencies),
        "mean_rtt_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p95_rtt_ms": percentile(latencies, 95),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def connectivity_check(run_dir: Path, scale: str) -> dict[str, Any]:
    result = run_logged(run_dir, ["kubectl", "get", "nodes", "-l", f"idynamics.dev/{scale}=true"], timeout=60, check=False)
    dns = run_logged(
        run_dir,
        ["kubectl", "-n", "kube-system", "get", "pods", "-l", "k8s-app=kube-dns", "-o", "wide"],
        timeout=60,
        check=False,
    )
    return {
        "kubectl_nodes_rc": result.returncode,
        "kubectl_nodes_first_line": result.stdout.splitlines()[0] if result.stdout else "",
        "dns_pods_rc": dns.returncode,
        "dns_ready_mentions": dns.stdout.count("Running"),
    }


def archive_cluster_checks(run_dir: Path, label: str, scale: str) -> dict[str, Any]:
    captures = {
        f"env/{label}_nodes.txt": ["kubectl", "get", "nodes", "-l", f"idynamics.dev/{scale}=true", "-o", "wide"],
        f"env/{label}_coredns_pods.txt": [
            "kubectl",
            "-n",
            "kube-system",
            "get",
            "pods",
            "-l",
            "k8s-app=kube-dns",
            "-o",
            "wide",
        ],
        f"env/{label}_coredns_service.txt": ["kubectl", "-n", "kube-system", "get", "svc", "kube-dns", "-o", "wide"],
        f"env/{label}_coredns_endpoints.txt": ["kubectl", "-n", "kube-system", "get", "endpoints", "kube-dns", "-o", "yaml"],
    }
    summary: dict[str, Any] = {}
    for rel, cmd in captures.items():
        result = run_logged(run_dir, cmd, timeout=60, check=False)
        write(run_dir / rel, result.stdout)
        if result.stderr:
            write(run_dir / f"{rel}.err", result.stderr)
        summary[Path(rel).stem + "_rc"] = result.returncode
    summary.update(connectivity_check(run_dir, scale))
    return summary


def validate_scale(scale: str, args: argparse.Namespace) -> Path:
    run_id = f"live-tc-validation-{scale}-{utc_stamp()}"
    run_dir = init_run(
        run_id,
        "qdisc_target_vs_measured_validation",
        {
            "scale": scale,
            "latency_target_ms": args.latency_ms,
            "bandwidth_target_mbps": args.bandwidth_mbps,
            "worker_only": True,
            "traffic_scope": "destination-specific selected worker node IPs",
        },
    )
    with ExperimentLock(run_id):
        nodes = selected_nodes(scale)
        write(run_dir / "raw" / "nodes.json", json.dumps(nodes, indent=2) + "\n")
        snapshot(run_dir, "qdisc_before", scale)
        pairs = [(nodes[i]["ip"], nodes[(i + 1) % len(nodes)]["ip"]) for i in range(min(len(nodes), args.max_pairs))]
        before = [ping_measure(src, dst, run_dir) for src, dst in pairs]
        write(run_dir / "raw" / "ping_before.json", json.dumps(before, indent=2) + "\n")
        try:
            apply_tc(nodes, run_dir, args.latency_ms, args.bandwidth_mbps)
            snapshot(run_dir, "qdisc_after_apply", scale)
            during = [ping_measure(src, dst, run_dir) for src, dst in pairs]
            write(run_dir / "raw" / "ping_during.json", json.dumps(during, indent=2) + "\n")
        finally:
            reset_tc(run_dir, scale)
            snapshot(run_dir, "qdisc_after_reset", scale)
        after = [ping_measure(src, dst, run_dir) for src, dst in pairs]
        write(run_dir / "raw" / "ping_after_reset.json", json.dumps(after, indent=2) + "\n")
        summary = summarize_validation(run_dir, scale, args.latency_ms)
        write(run_dir / "processed" / "tc_validation_metrics.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
        write_validation_summary(run_dir, scale, summary)
    return run_dir


def summarize_validation(run_dir: Path, scale: str, latency_target_ms: float) -> dict[str, Any]:
    before = json.loads((run_dir / "raw" / "ping_before.json").read_text())
    during = json.loads((run_dir / "raw" / "ping_during.json").read_text())
    after = json.loads((run_dir / "raw" / "ping_after_reset.json").read_text())
    before_mean = statistics.fmean(row["mean_rtt_ms"] for row in before if row["samples"]) if before else 0.0
    during_mean = statistics.fmean(row["mean_rtt_ms"] for row in during if row["samples"]) if during else 0.0
    after_mean = statistics.fmean(row["mean_rtt_ms"] for row in after if row["samples"]) if after else 0.0
    expected = before_mean + 2.0 * latency_target_ms
    return {
        "pairs": len(during),
        "before_mean_rtt_ms": before_mean,
        "during_mean_rtt_ms": during_mean,
        "after_reset_mean_rtt_ms": after_mean,
        "target_one_way_delay_ms": latency_target_ms,
        "expected_during_rtt_ms": expected,
        "target_vs_measured_error_ms": during_mean - expected,
        "reset_residual_rtt_ms": after_mean - before_mean,
        "connectivity_after_reset": connectivity_check(run_dir, scale),
    }


def write_validation_summary(run_dir: Path, scale: str, metrics: dict[str, Any]) -> None:
    write(
        run_dir / "summary.md",
        f"""# {run_dir.name}

Status: completed

## Purpose
Validate destination-specific live tc delay application on worker-only `{scale}`.

## Result
- Mean RTT before tc: {metrics['before_mean_rtt_ms']:.2f} ms.
- Mean RTT during tc: {metrics['during_mean_rtt_ms']:.2f} ms.
- Expected RTT during tc: {metrics['expected_during_rtt_ms']:.2f} ms.
- Target-vs-measured error: {metrics['target_vs_measured_error_ms']:.2f} ms.
- Mean RTT after reset: {metrics['after_reset_mean_rtt_ms']:.2f} ms.
- Reset residual: {metrics['reset_residual_rtt_ms']:.2f} ms.

## Safety
Qdisc snapshots were captured before application, after application, before reset, and after reset. The injector only installed filters for selected worker destination node IPs; control-plane, Kubernetes service IPs, DNS ClusterIP, and SSH/control traffic to the master were not filter targets.
	""",
    )


def social_manifest(namespace: str, scale: str, image: str, placement: str) -> str:
    scale_label = f"idynamics.dev/{scale}"
    server_indented = "\n".join(f"    {line}" for line in SOCIAL_SERVER.splitlines())
    services = (
        "nginx-thrift",
        "compose-post-service",
        "home-timeline-service",
        "user-timeline-service",
        "user-service",
        "text-service",
        "unique-id-service",
        "media-service",
    )
    affinity = ""
    if placement == "policy1":
        affinity = """
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 80
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: live-social
              topologyKey: kubernetes.io/hostname
"""
    elif placement == "policy4":
        affinity = """
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 70
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  role: frontend
              topologyKey: kubernetes.io/hostname
"""
    pieces = [
        f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    benchmark: live-social-network
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
    for service in services:
        role = "frontend" if service == "nginx-thrift" else "backend"
        pieces.append(
            f"""---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service}
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: live-social
      component: {service}
  template:
    metadata:
      labels:
        app: live-social
        component: {service}
        role: {role}
        placement-policy: {placement}
    spec:
      nodeSelector:
        {scale_label}: "true"
{affinity if service != "nginx-thrift" else ""}
      containers:
      - name: server
        image: {image}
        imagePullPolicy: IfNotPresent
        command: ["python3", "/app/server.py"]
        env:
        - name: ROLE
          value: "{service}"
        - name: DELAY_MS
          value: "2.0"
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
spec:
  selector:
    app: live-social
    component: {service}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
"""
        )
    return "\n".join(pieces)


def request_once(base_url: str, idx: int) -> dict[str, Any]:
    endpoint = SOCIAL_ENDPOINTS[idx % len(SOCIAL_ENDPOINTS)]
    started = time.perf_counter()
    status = 0
    error = ""
    try:
        with urllib.request.urlopen(base_url + endpoint, timeout=10) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = str(exc)
    except Exception as exc:
        error = repr(exc)
    return {"request_id": idx, "endpoint": endpoint, "status": status, "latency_ms": (time.perf_counter() - started) * 1000.0, "error": error}


def run_load(
    run_dir: Path,
    namespace: str,
    placement: str,
    requests: int,
    concurrency: int,
    repetition: int = 1,
) -> dict[str, Any]:
    proc = start_port_forward(run_dir, namespace, 18080, "nginx-thrift", 8080)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(request_once, "http://127.0.0.1:18080", idx) for idx in range(requests)]
            for future in as_completed(futures):
                rows.append(future.result())
    finally:
        elapsed = time.perf_counter() - started
        stop_process(proc)
    rows.sort(key=lambda row: int(row["request_id"]))
    suffix = f"{placement}_rep{repetition}"
    with (run_dir / "raw" / f"{suffix}_loadgen.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["request_id", "endpoint", "status", "latency_ms", "error"])
        writer.writeheader()
        writer.writerows(rows)
    latencies = [float(row["latency_ms"]) for row in rows if int(row["status"]) == 200]
    return {
        "placement": placement,
        "repetition": repetition,
        "requests": len(rows),
        "success": len(latencies),
        "errors": len(rows) - len(latencies),
        "p50_latency_ms": percentile(latencies, 50),
        "p95_latency_ms": percentile(latencies, 95),
        "p99_latency_ms": percentile(latencies, 99),
        "mean_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "throughput_rps": len(latencies) / elapsed if elapsed else 0.0,
    }


def collect_ns(run_dir: Path, namespace: str, prefix: str) -> None:
    for rel, cmd in {
        f"raw/{prefix}_pods_wide.txt": ["kubectl", "-n", namespace, "get", "pods", "-o", "wide"],
        f"raw/{prefix}_pods.json": ["kubectl", "-n", namespace, "get", "pods", "-o", "json"],
        f"raw/{prefix}_events.txt": ["kubectl", "-n", namespace, "get", "events", "--sort-by=.lastTimestamp"],
    }.items():
        result = run_logged(run_dir, cmd, timeout=60, check=False)
        write(run_dir / rel, result.stdout)
        if result.stderr:
            write(run_dir / f"{rel}.err", result.stderr)


def run_social_live(args: argparse.Namespace) -> Path:
    run_id = f"live-tc-social-{args.scale}-{utc_stamp()}"
    run_dir = init_run(
        run_id,
        "live_tc_social_network_policy_comparison",
        {
            "scale": args.scale,
            "requests": args.requests,
            "concurrency": args.concurrency,
            "repetitions": args.repetitions,
            "latency_target_ms": args.latency_ms,
            "bandwidth_target_mbps": args.bandwidth_mbps,
            "tc_matrix_source": "burst_correlated_frame",
            "tc_matrix_frame_index": args.tc_frame_index,
            "policies": ["kubernetes", "policy1", "policy4"],
        },
    )
    with ExperimentLock(run_id):
        nodes = selected_nodes(args.scale)
        write(run_dir / "raw" / "nodes.json", json.dumps(nodes, indent=2) + "\n")
        frames = list(BurstCorrelatedProvider(num_nodes=len(nodes), steps=24, interval_s=5.0, seed=41).frames())
        tc_frame = frames[min(args.tc_frame_index, len(frames) - 1)]
        write_frames_csv(frames, run_dir / "raw" / "burst_correlated_trace.csv")
        write_frames_csv([tc_frame], run_dir / "raw" / "applied_tc_matrix.csv")
        write_metrics_json(compute_network_metrics(frames), run_dir / "processed" / "trace_metrics.json")
        snapshot(run_dir, "qdisc_before", args.scale)
        side_before = archive_cluster_checks(run_dir, "before_tc", args.scale)
        metrics: list[dict[str, Any]] = []
        try:
            apply_tc(nodes, run_dir, args.latency_ms, args.bandwidth_mbps, frame=tc_frame)
            snapshot(run_dir, "qdisc_after_apply", args.scale)
            side_after_apply = archive_cluster_checks(run_dir, "after_tc_apply", args.scale)
            for repetition in range(1, args.repetitions + 1):
                for placement in ("kubernetes", "policy1", "policy4"):
                    namespace = f"{run_id}-{placement}-rep{repetition}".lower()
                    manifest = social_manifest(namespace, args.scale, args.image, placement)
                    write(run_dir / "raw" / f"{placement}_rep{repetition}_manifest.yaml", manifest)
                    result = run_logged(run_dir, ["kubectl", "apply", "-f", "-"], timeout=120, check=False, input_text=manifest)
                    write(run_dir / "logs" / f"{placement}_rep{repetition}_apply.stdout", result.stdout)
                    write(run_dir / "logs" / f"{placement}_rep{repetition}_apply.stderr", result.stderr)
                    if result.returncode != 0:
                        raise RuntimeError(result.stderr)
                    run_logged(run_dir, ["kubectl", "-n", namespace, "wait", "--for=condition=available", "deployment", "--all", f"--timeout={args.ready_timeout}s"], timeout=args.ready_timeout + 40)
                    collect_ns(run_dir, namespace, f"{placement}_rep{repetition}_ready")
                    metrics.append(run_load(run_dir, namespace, placement, args.requests, args.concurrency, repetition))
                    collect_ns(run_dir, namespace, f"{placement}_rep{repetition}_after")
                    if not args.keep:
                        run_logged(run_dir, ["kubectl", "delete", "namespace", namespace, "--ignore-not-found=true", "--wait=false"], timeout=60, check=False)
        finally:
            archive_cluster_checks(run_dir, "before_tc_reset", args.scale)
            reset_tc(run_dir, args.scale)
            snapshot(run_dir, "qdisc_after_reset", args.scale)
        side_after = archive_cluster_checks(run_dir, "after_tc_reset", args.scale)
        aggregate = aggregate_social_metrics(metrics)
        write(
            run_dir / "processed" / "social_live_tc_metrics.json",
            json.dumps(
                {
                    "policies": metrics,
                    "aggregates": aggregate,
                    "side_effects_before": side_before,
                    "side_effects_after_apply": side_after_apply,
                    "side_effects_after": side_after,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        write_social_summary(run_dir, args.scale, metrics, aggregate, side_before, side_after)
    return run_dir


def aggregate_social_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates: list[dict[str, Any]] = []
    for placement in ("kubernetes", "policy1", "policy4"):
        rows = [row for row in metrics if row["placement"] == placement]
        if not rows:
            continue
        aggregates.append(
            {
                "placement": placement,
                "repetitions": len(rows),
                "requests": sum(int(row["requests"]) for row in rows),
                "success": sum(int(row["success"]) for row in rows),
                "errors": sum(int(row["errors"]) for row in rows),
                "mean_p50_latency_ms": statistics.fmean(float(row["p50_latency_ms"]) for row in rows),
                "mean_p95_latency_ms": statistics.fmean(float(row["p95_latency_ms"]) for row in rows),
                "mean_p99_latency_ms": statistics.fmean(float(row["p99_latency_ms"]) for row in rows),
                "mean_latency_ms": statistics.fmean(float(row["mean_latency_ms"]) for row in rows),
                "mean_throughput_rps": statistics.fmean(float(row["throughput_rps"]) for row in rows),
            }
        )
    return aggregates


def write_social_summary(
    run_dir: Path,
    scale: str,
    metrics: list[dict[str, Any]],
    aggregate: list[dict[str, Any]],
    side_before: dict[str, Any],
    side_after: dict[str, Any],
) -> None:
    rows = "\n".join(
        f"| {m['placement']} | {m['repetition']} | {m['success']}/{m['requests']} | {m['p50_latency_ms']:.2f} | {m['p95_latency_ms']:.2f} | {m['p99_latency_ms']:.2f} | {m['throughput_rps']:.2f} |"
        for m in metrics
    )
    aggregate_rows = "\n".join(
        f"| {m['placement']} | {m['repetitions']} | {m['success']}/{m['requests']} | {m['mean_p50_latency_ms']:.2f} | {m['mean_p95_latency_ms']:.2f} | {m['mean_p99_latency_ms']:.2f} | {m['mean_throughput_rps']:.2f} |"
        for m in aggregate
    )
    write(
        run_dir / "summary.md",
        f"""# {run_dir.name}

Status: completed

## Purpose
Run a live destination-specific tc application experiment on Social Network-compatible traffic for Kubernetes baseline, Policy 1, and Policy 4 placement modes.

## Results
| Placement | Rep | Success | p50 ms | p95 ms | p99 ms | rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{rows}

## Aggregate
| Placement | Reps | Success | mean p50 ms | mean p95 ms | mean p99 ms | mean rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{aggregate_rows}

## Side Effects
- Before tc: kubectl node check rc={side_before['kubectl_nodes_rc']}, DNS running mentions={side_before['dns_ready_mentions']}.
- After reset: kubectl node check rc={side_after['kubectl_nodes_rc']}, DNS running mentions={side_after['dns_ready_mentions']}.
- Qdisc snapshots are archived in env/qdisc_before, env/qdisc_after_apply, env/qdisc_before_reset, and env/qdisc_after_reset.
- The exact applied matrix is archived in raw/applied_tc_matrix.csv; the full burst-correlated trace is archived in raw/burst_correlated_trace.csv.

## Boundary
The tc filters target selected worker node IP destinations. On this Calico overlay cluster that is the practical live path for pod-to-pod traffic, but it can also delay other worker-to-worker overlay packets among the selected workers. The run therefore reports side-effect checks and avoids claims that non-experimental worker-to-worker overlay traffic is completely untouched.
	""",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--scales", nargs="+", choices=SCALES, default=list(SCALES))
    validate.add_argument("--latency-ms", type=float, default=20.0)
    validate.add_argument("--bandwidth-mbps", type=float, default=300.0)
    validate.add_argument("--max-pairs", type=int, default=6)
    social = sub.add_parser("social-live")
    social.add_argument("--scale", choices=SCALES, default="scale10")
    social.add_argument("--latency-ms", type=float, default=20.0)
    social.add_argument("--bandwidth-mbps", type=float, default=300.0)
    social.add_argument("--requests", type=int, default=60)
    social.add_argument("--concurrency", type=int, default=8)
    social.add_argument("--repetitions", type=int, default=1)
    social.add_argument("--tc-frame-index", type=int, default=12)
    social.add_argument("--ready-timeout", type=int, default=240)
    social.add_argument("--image", default="python:3.11-slim")
    social.add_argument("--keep", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "validate":
        for scale in args.scales:
            print(validate_scale(scale, args))
    elif args.command == "social-live":
        print(run_social_live(args))


if __name__ == "__main__":
    main()
