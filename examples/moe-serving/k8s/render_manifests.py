#!/usr/bin/env python3
"""Render Kubernetes manifests for the MoE serving microbenchmark."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experts", type=int, default=4)
    parser.add_argument(
        "--policy",
        choices=["default", "kubernetes-default", "idynamics", "cga", "hda", "policy1", "policy2", "policy3", "policy4"],
        default="default",
    )
    parser.add_argument("--hot-experts", default="0,1")
    parser.add_argument("--namespace", default="moe-serving")
    parser.add_argument("--image", default=os.getenv("MOE_IMAGE", "moe-serving:latest"))
    parser.add_argument("--compute-delay-ms", type=float, default=5.0)
    parser.add_argument("--payload-bytes", type=int, default=256)
    parser.add_argument("--cache-hit-ratio", type=float, default=0.0)
    parser.add_argument("--node-pool-label", default="")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def normalize_policy(policy: str) -> str:
    aliases = {
        "kubernetes-default": "default",
        "cga": "policy1",
        "hda": "policy4",
        "idynamics": "policy1",
    }
    return aliases.get(policy, policy)


def placement_group(policy: str, role: str, hot_experts: set[int], expert_id: int | None = None) -> str:
    policy = normalize_policy(policy)
    if policy in {"idynamics", "policy1"}:
        if role in {"frontend", "tokenizer", "router", "aggregator", "cache"}:
            return "moe-hot-path"
        return "moe-hot-path" if expert_id in hot_experts else "moe-cold"
    if policy == "policy2":
        if role in {"frontend", "tokenizer", "router", "aggregator"}:
            return "moe-low-delay"
        return "moe-low-delay" if expert_id in hot_experts else "moe-cold"
    if policy == "policy3":
        if role in {"router", "aggregator"}:
            return "moe-high-bandwidth"
        return "moe-high-bandwidth" if expert_id in hot_experts else "moe-cold"
    if policy == "policy4":
        if role in {"frontend", "tokenizer", "router", "aggregator"}:
            return "moe-hybrid"
        return "moe-hybrid" if expert_id in hot_experts else "moe-cold"
    return ""


def affinity(policy: str, role: str, hot_experts: set[int], expert_id: int | None = None) -> str:
    group = placement_group(policy, role, hot_experts, expert_id)
    if not group:
        return ""
    return f"""
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 80
            preference:
              matchExpressions:
              - key: idynamics.io/placement-group
                operator: In
                values: ["{group}"]
"""


def node_selector(node_pool_label: str) -> str:
    if not node_pool_label:
        return ""
    if "=" not in node_pool_label:
        raise ValueError("--node-pool-label must have key=value form")
    key, value = node_pool_label.split("=", 1)
    return f"""
      nodeSelector:
        {key}: "{value}"
"""


def deployment(name: str, role: str, image: str, namespace: str, experts: int, delay: float, payload: int, cache_hit_ratio: float, policy: str, hot_experts: set[int], node_pool_label: str, expert_id: int | None = None) -> str:
    normalized_policy = normalize_policy(policy)
    env = [
        ("MOE_ROLE", role),
        ("SERVICE_NAME", name),
        ("EXPERTS", str(experts)),
        ("COMPUTE_DELAY_MS", str(delay)),
        ("EXPERT_DELAY_MS", str(delay)),
        ("PAYLOAD_BYTES", str(payload)),
        ("CACHE_HIT_RATIO", str(cache_hit_ratio)),
    ]
    if expert_id is not None:
        env.append(("EXPERT_ID", str(expert_id)))
    env_yaml = "\n".join(f"        - name: {key}\n          value: \"{value}\"" for key, value in env)
    return f"""---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: moe-serving
    component: {name}
    placement-policy: {policy}
    idynamics.io/policy: {normalized_policy}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: moe-serving
      component: {name}
  template:
    metadata:
      labels:
        app: moe-serving
        component: {name}
        placement-policy: {policy}
        idynamics.io/policy: {normalized_policy}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:{node_selector(node_pool_label)}{affinity(policy, role, hot_experts, expert_id)}
      containers:
      - name: {name}
        image: {image}
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
          name: http
        env:
{env_yaml}
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 2
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 96Mi
          limits:
            cpu: 500m
            memory: 256Mi
"""


def service(name: str, namespace: str) -> str:
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


def main() -> None:
    args = parse_args()
    if args.experts < 1:
        raise SystemExit("--experts must be >= 1")
    hot_experts = {int(item) for item in args.hot_experts.split(",") if item.strip()}
    pieces = [
        f"""apiVersion: v1
kind: Namespace
metadata:
  name: {args.namespace}
  labels:
    app: moe-serving
""",
    ]
    for role in ["frontend", "tokenizer", "router", "aggregator", "cache"]:
        pieces.append(deployment(role, role, args.image, args.namespace, args.experts, args.compute_delay_ms, args.payload_bytes, args.cache_hit_ratio, args.policy, hot_experts, args.node_pool_label))
        pieces.append(service(role, args.namespace))
    for expert in range(args.experts):
        name = f"expert-{expert}"
        pieces.append(deployment(name, "expert", args.image, args.namespace, args.experts, args.compute_delay_ms, args.payload_bytes, args.cache_hit_ratio, args.policy, hot_experts, args.node_pool_label, expert))
        pieces.append(service(name, args.namespace))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(pieces) + "\n")


if __name__ == "__main__":
    main()
