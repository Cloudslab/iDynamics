#!/usr/bin/env python3
"""Collect benchmark pod/node occupancy from Kubernetes JSON."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_EXCLUDED_COMPONENTS = {"loadgenerator", "load-generator", "client", "wrk", "fortio"}


def is_ready_node(node: dict[str, Any]) -> bool:
    return any(
        cond.get("type") == "Ready" and cond.get("status") == "True"
        for cond in node.get("status", {}).get("conditions", [])
    )


def selected_worker_nodes(nodes_json: dict[str, Any], scale: str, label_prefix: str = "idynamics.dev") -> list[str]:
    label = f"{label_prefix}/{scale}"
    nodes = []
    for node in nodes_json.get("items", []):
        labels = node.get("metadata", {}).get("labels", {})
        if labels.get(label) == "true" and is_ready_node(node):
            nodes.append(node.get("metadata", {}).get("name", ""))
    return sorted(name for name in nodes if name)


def pod_component(pod: dict[str, Any]) -> str:
    metadata = pod.get("metadata", {})
    labels = metadata.get("labels", {})
    for key in ("component", "app", "app.kubernetes.io/name", "run"):
        if labels.get(key):
            return str(labels[key])
    name = str(metadata.get("name", ""))
    return name.rsplit("-", 2)[0] if "-" in name else name


def is_ready_pod(pod: dict[str, Any]) -> bool:
    return any(
        cond.get("type") == "Ready" and cond.get("status") == "True"
        for cond in pod.get("status", {}).get("conditions", [])
    )


def active_app_pods(
    pods_json: dict[str, Any],
    namespace: str,
    selected_nodes: set[str],
    excluded_components: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded = excluded_components or DEFAULT_EXCLUDED_COMPONENTS
    pods = []
    for pod in pods_json.get("items", []):
        metadata = pod.get("metadata", {})
        if metadata.get("namespace") != namespace:
            continue
        if metadata.get("deletionTimestamp"):
            continue
        phase = pod.get("status", {}).get("phase")
        if phase in {"Succeeded", "Failed"}:
            continue
        component = pod_component(pod)
        if component in excluded:
            continue
        node_name = pod.get("spec", {}).get("nodeName", "")
        if node_name and node_name not in selected_nodes:
            continue
        pods.append(pod)
    return pods


def occupancy_metrics(
    nodes_json: dict[str, Any],
    pods_json: dict[str, Any],
    *,
    namespace: str,
    scale: str,
    label_prefix: str = "idynamics.dev",
    excluded_components: set[str] | None = None,
) -> dict[str, Any]:
    selected_nodes = selected_worker_nodes(nodes_json, scale, label_prefix)
    selected_set = set(selected_nodes)
    app_pods = active_app_pods(pods_json, namespace, selected_set, excluded_components)
    node_counts = Counter(pod.get("spec", {}).get("nodeName", "") for pod in app_pods)
    node_counts.pop("", None)
    non_empty_worker_nodes = len(node_counts)
    worker_nodes_selected = len(selected_nodes)
    ratio = non_empty_worker_nodes / worker_nodes_selected if worker_nodes_selected else 0.0
    ready_app_pods = sum(1 for pod in app_pods if is_ready_pod(pod))
    empty_worker_nodes = max(0, worker_nodes_selected - non_empty_worker_nodes)
    mean_pods = (len(app_pods) / non_empty_worker_nodes) if non_empty_worker_nodes else 0.0
    max_pods = max(node_counts.values(), default=0)
    evidence_label = "saturated application scaling" if ratio >= 0.70 else "worker-pool/candidate-space evidence"
    return {
        "worker_nodes_selected": worker_nodes_selected,
        "actual_app_pods": len(app_pods),
        "ready_app_pods": ready_app_pods,
        "non_empty_worker_nodes": non_empty_worker_nodes,
        "pod_node_occupancy_ratio": ratio,
        "empty_worker_nodes": empty_worker_nodes,
        "mean_app_pods_per_non_empty_node": mean_pods,
        "max_app_pods_per_node": max_pods,
        "evidence_label": evidence_label,
        "selected_worker_nodes": selected_nodes,
        "pods_per_node": dict(sorted(node_counts.items())),
    }


def kubectl_json(args: list[str]) -> dict[str, Any]:
    result = subprocess.run(["kubectl", *args, "-o", "json"], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def write_outputs(metrics: dict[str, Any], json_path: Path | None, csv_path: Path | None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        scalar = {key: value for key, value in metrics.items() if not isinstance(value, (list, dict))}
        with csv_path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(scalar))
            writer.writeheader()
            writer.writerow(scalar)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--scale", required=True, choices=["scale5", "scale10", "scale20", "scale30", "scale45"])
    parser.add_argument("--label-prefix", default="idynamics.dev")
    parser.add_argument("--exclude-component", action="append", default=[])
    parser.add_argument("--nodes-json", type=Path)
    parser.add_argument("--pods-json", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-csv", type=Path)
    args = parser.parse_args()

    nodes = json.loads(args.nodes_json.read_text()) if args.nodes_json else kubectl_json(["get", "nodes"])
    pods = json.loads(args.pods_json.read_text()) if args.pods_json else kubectl_json(["get", "pods", "-n", args.namespace])
    excluded = DEFAULT_EXCLUDED_COMPONENTS | set(args.exclude_component)
    metrics = occupancy_metrics(
        nodes,
        pods,
        namespace=args.namespace,
        scale=args.scale,
        label_prefix=args.label_prefix,
        excluded_components=excluded,
    )
    write_outputs(metrics, args.output_json, args.output_csv)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
