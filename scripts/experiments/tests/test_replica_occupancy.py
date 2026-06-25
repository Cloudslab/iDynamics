from __future__ import annotations

import json
from pathlib import Path

from scripts.evaluation.collect_pod_node_occupancy import occupancy_metrics


REPO_ROOT = Path(__file__).resolve().parents[3]


def ready_node(name: str, scale: str | None = None) -> dict:
    labels = {}
    if scale:
        labels[f"idynamics.dev/{scale}"] = "true"
    return {
        "metadata": {"name": name, "labels": labels},
        "status": {"conditions": [{"type": "Ready", "status": "True"}]},
    }


def pod(name: str, namespace: str, component: str, node: str, ready: bool = True) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace, "labels": {"component": component}},
        "spec": {"nodeName": node},
        "status": {
            "phase": "Running",
            "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
        },
    }


def test_replica_profiles_keep_stateful_services_single_replica() -> None:
    online = json.loads((REPO_ROOT / "benchmarks/online-boutique/adapter/replica_profiles.yaml").read_text())
    moe = json.loads((REPO_ROOT / "benchmarks/moe-serving/adapter/replica_profiles.yaml").read_text())

    assert set(online["replica_profiles"]) == {"replica1", "replica3", "replica5"}
    assert set(moe["replica_profiles"]) == {"replica1", "replica3", "replica5"}
    assert online["replica_profiles"]["replica5"]["stateless_replicas"] == 5
    assert "redis-cart" in online["replica_profiles"]["replica5"]["single_replica_services"]
    assert moe["replica_profiles"]["replica5"]["expert_replicas"] == 5
    assert "cache" in moe["replica_profiles"]["replica5"]["single_replica_services"]


def test_occupancy_metrics_label_sparse_worker_pool_evidence() -> None:
    nodes = {"items": [ready_node(f"w{i}", "scale45") for i in range(1, 46)]}
    pods = {
        "items": [
            pod("frontend-1", "shop", "frontend", "w1"),
            pod("cart-1", "shop", "cartservice", "w2"),
            pod("loadgenerator-1", "shop", "loadgenerator", "w3"),
            pod("frontend-2", "other", "frontend", "w4"),
        ]
    }

    metrics = occupancy_metrics(nodes, pods, namespace="shop", scale="scale45")

    assert metrics["worker_nodes_selected"] == 45
    assert metrics["actual_app_pods"] == 2
    assert metrics["ready_app_pods"] == 2
    assert metrics["non_empty_worker_nodes"] == 2
    assert metrics["empty_worker_nodes"] == 43
    assert metrics["pod_node_occupancy_ratio"] == 2 / 45
    assert metrics["evidence_label"] == "worker-pool/candidate-space evidence"


def test_occupancy_metrics_label_saturated_application_scaling() -> None:
    nodes = {"items": [ready_node(f"w{i}", "scale20") for i in range(1, 21)]}
    pods = {"items": [pod(f"svc-{i}", "moe", "expert", f"w{i}") for i in range(1, 16)]}

    metrics = occupancy_metrics(nodes, pods, namespace="moe", scale="scale20")

    assert metrics["worker_nodes_selected"] == 20
    assert metrics["non_empty_worker_nodes"] == 15
    assert metrics["pod_node_occupancy_ratio"] == 0.75
    assert metrics["evidence_label"] == "saturated application scaling"
