#!/usr/bin/env python3
"""Run built-in iDynamics placement planners from JSON or built-in MoE data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idynamics.policies import make_policy
from idynamics.types import NetworkMatrix, NodeInfo, PodInfo, ServiceGraph, TrafficEdge


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run built-in iDynamics placement planners from JSON or a built-in demo.")
    parser.add_argument("--policy", choices=["policy1", "policy2", "policy3", "policy4"], required=True, help="Policy planner to execute.")
    parser.add_argument("--input", type=Path, help="JSON file with pods, nodes, service_graph, and optional network.")
    parser.add_argument("--output", type=Path, help="Write placement plan JSON to this path instead of stdout.")
    parser.add_argument("--demo", choices=["moe"], help="Use a built-in smoke input when --input is omitted.")
    return parser.parse_args()


def demo_moe() -> dict[str, Any]:
    return {
        "nodes": [
            {"name": "node-a", "cpu_capacity_millicores": 2000, "memory_capacity_mib": 4096},
            {"name": "node-b", "cpu_capacity_millicores": 2000, "memory_capacity_mib": 4096},
            {"name": "node-c", "cpu_capacity_millicores": 2000, "memory_capacity_mib": 4096},
        ],
        "pods": [
            {"name": "frontend", "namespace": "moe", "service": "frontend", "cpu_request_millicores": 1000, "memory_request_mib": 256, "node_name": "node-a", "labels": {"idynamics.io/locked": "true"}},
            {"name": "aggregator", "namespace": "moe", "service": "aggregator", "cpu_request_millicores": 1000, "memory_request_mib": 256, "node_name": "node-c", "labels": {"idynamics.io/locked": "true"}},
            {"name": "router", "namespace": "moe", "service": "router", "cpu_request_millicores": 1000, "memory_request_mib": 256},
            {"name": "expert-0", "namespace": "moe", "service": "expert-0", "cpu_request_millicores": 1000, "memory_request_mib": 256},
            {"name": "expert-1", "namespace": "moe", "service": "expert-1", "cpu_request_millicores": 1000, "memory_request_mib": 256},
        ],
        "service_graph": {
            "services": ["frontend", "router", "expert-0", "expert-1", "aggregator"],
            "edges": [
                {"source": "frontend", "destination": "router", "request_rate": 1000, "sent_bytes_per_s": 100000, "received_bytes_per_s": 100000, "latency_ms": 1},
                {"source": "router", "destination": "expert-0", "request_rate": 200, "sent_bytes_per_s": 100000, "received_bytes_per_s": 100000, "latency_ms": 20},
                {"source": "expert-0", "destination": "aggregator", "request_rate": 200, "sent_bytes_per_s": 100000, "received_bytes_per_s": 100000, "latency_ms": 20},
                {"source": "router", "destination": "expert-1", "request_rate": 20, "sent_bytes_per_s": 5000000, "received_bytes_per_s": 5000000, "latency_ms": 2},
                {"source": "expert-1", "destination": "aggregator", "request_rate": 20, "sent_bytes_per_s": 5000000, "received_bytes_per_s": 5000000, "latency_ms": 2},
            ],
        },
        "network": {
            "node_names": ["node-a", "node-b", "node-c"],
            "latency_ms": [[0, 1, 20], [1, 0, 2], [20, 2, 0]],
            "bandwidth_mbps": [[1000000, 80, 1000], [80, 1000000, 1000], [1000, 1000, 1000000]],
        },
    }


def load_input(args: argparse.Namespace) -> dict[str, Any]:
    if args.input:
        try:
            return json.loads(args.input.read_text())
        except FileNotFoundError as exc:
            raise SystemExit(f"input file not found: {args.input}") from exc
        except json.JSONDecodeError as exc:
            raise SystemExit(f"input file is not valid JSON: {args.input}: {exc}") from exc
    if args.demo == "moe":
        return demo_moe()
    raise SystemExit("provide --input or --demo moe")


def build_objects(data: dict[str, Any]) -> tuple[list[PodInfo], list[NodeInfo], ServiceGraph | None, NetworkMatrix | None]:
    try:
        nodes = [NodeInfo(**item) for item in data["nodes"]]
        pods = [PodInfo(**item) for item in data["pods"]]
    except KeyError as exc:
        raise ValueError(f"missing required input section: {exc.args[0]}") from exc
    except TypeError as exc:
        raise ValueError(f"invalid pod or node input: {exc}") from exc
    graph = None
    if data.get("service_graph"):
        graph_data = data["service_graph"]
        graph = ServiceGraph(
            services=tuple(graph_data["services"]),
            edges=tuple(TrafficEdge(**edge) for edge in graph_data["edges"]),
            timestamp_s=graph_data.get("timestamp_s"),
        )
    network = None
    if data.get("network"):
        network_data = data["network"]
        network = NetworkMatrix.from_lists(
            network_data["node_names"],
            network_data["latency_ms"],
            network_data["bandwidth_mbps"],
            network_data.get("timestamp_s", 0.0),
        )
    return pods, nodes, graph, network


def main() -> None:
    args = parse_args()
    try:
        pods, nodes, graph, network = build_objects(load_input(args))
        plan = make_policy(args.policy).plan_with_details(pods, nodes, graph, network)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    out = {
        "policy": plan.policy,
        "objective_cost": plan.objective_cost,
        "placement": dict(plan.placement),
        "decisions": [
            {
                "pod_name": decision.pod_name,
                "source_node": decision.source_node,
                "target_node": decision.target_node,
                "policy": decision.policy,
                "score": decision.score,
                "reason": decision.reason,
            }
            for decision in plan.decisions
        ],
    }
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
