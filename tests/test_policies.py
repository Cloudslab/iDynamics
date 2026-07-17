from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from idynamics.policies import make_policy
from idynamics.types import NetworkMatrix, NodeInfo, PodInfo, ServiceGraph, TrafficEdge


def toy_inputs() -> tuple[list[PodInfo], list[NodeInfo], ServiceGraph, NetworkMatrix]:
    nodes = [
        NodeInfo("n0", 2000, 4096),
        NodeInfo("n1", 2000, 4096),
        NodeInfo("n2", 2000, 4096),
    ]
    pods = [
        PodInfo("frontend", "toy", 1000, 100, service="frontend", node_name="n0", labels={"idynamics.io/locked": "true"}),
        PodInfo("aggregator", "toy", 1000, 100, service="aggregator", node_name="n2", labels={"idynamics.io/locked": "true"}),
        PodInfo("router", "toy", 1000, 100, service="router"),
        PodInfo("expert-small", "toy", 1000, 100, service="expert-small"),
        PodInfo("expert-large", "toy", 1000, 100, service="expert-large"),
    ]
    graph = ServiceGraph(
        services=("frontend", "router", "expert-small", "expert-large", "aggregator"),
        edges=(
            TrafficEdge("frontend", "router", request_rate=1000, sent_bytes_per_s=100000, received_bytes_per_s=100000, latency_ms=1),
            TrafficEdge("router", "expert-small", request_rate=200, sent_bytes_per_s=100000, received_bytes_per_s=100000, latency_ms=20),
            TrafficEdge("expert-small", "aggregator", request_rate=200, sent_bytes_per_s=100000, received_bytes_per_s=100000, latency_ms=20),
            TrafficEdge("router", "expert-large", request_rate=20, sent_bytes_per_s=5000000, received_bytes_per_s=5000000, latency_ms=2),
            TrafficEdge("expert-large", "aggregator", request_rate=20, sent_bytes_per_s=5000000, received_bytes_per_s=5000000, latency_ms=2),
        ),
    )
    network = NetworkMatrix.from_lists(
        ["n0", "n1", "n2"],
        [[0, 1, 20], [1, 0, 1], [20, 1, 0]],
        [[1000000, 50, 1000], [50, 1000000, 1000], [1000, 1000, 1000000]],
    )
    return pods, nodes, graph, network


def placements() -> dict[str, dict[str, str]]:
    pods, nodes, graph, network = toy_inputs()
    return {
        name: dict(make_policy(name).plan_with_details(pods, nodes, graph, network).placement)
        for name in ("policy1", "policy2", "policy3", "policy4")
    }


def test_policy2_is_latency_critical_path_not_policy1() -> None:
    result = placements()
    assert result["policy1"]["router"] == "n0"
    assert result["policy2"]["router"] == "n1"
    assert result["policy2"] != result["policy1"]


def test_policy3_is_payload_bandwidth_aware_not_policy1_or_policy2() -> None:
    result = placements()
    assert result["policy3"]["router"] == "n1"
    assert result["policy3"]["expert-large"] == "n2"
    assert result["policy3"] != result["policy1"]
    assert result["policy3"] != result["policy2"]


def test_all_policy_cli_entrypoints_emit_a_plan() -> None:
    script = Path("scripts/policies/run_policy.py")
    for policy in ("policy1", "policy2", "policy3", "policy4"):
        completed = subprocess.run(
            [sys.executable, str(script), "--policy", policy, "--demo", "moe"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        payload = json.loads(completed.stdout)
        assert payload["policy"].startswith(policy)
        assert payload["placement"]["frontend"] == "node-a"
        assert payload["decisions"]
