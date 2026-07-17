"""Small pure helpers for baseline policy tests and examples."""

from __future__ import annotations

from collections.abc import Sequence

from idynamics.types import NodeInfo, PodInfo, SchedulingDecision


def score_node_for_pod(node: NodeInfo, pod: PodInfo) -> float:
    """Score a node by normalized residual capacity after placing a pod."""
    if not node.ready:
        return float("-inf")
    cpu_after = node.cpu_free_millicores - pod.cpu_request_millicores
    mem_after = node.memory_free_mib - pod.memory_request_mib
    if cpu_after < 0 or mem_after < 0:
        return float("-inf")
    cpu_ratio = cpu_after / max(1.0, node.cpu_capacity_millicores)
    mem_ratio = mem_after / max(1.0, node.memory_capacity_mib)
    return min(cpu_ratio, mem_ratio)


def first_fit_decision(pod: PodInfo, nodes: Sequence[NodeInfo], policy: str = "first-fit") -> SchedulingDecision:
    ranked = sorted(((score_node_for_pod(node, pod), node) for node in nodes), key=lambda item: (-item[0], item[1].name))
    if not ranked or ranked[0][0] == float("-inf"):
        raise ValueError(f"no feasible node for pod {pod.namespace}/{pod.name}")
    score, node = ranked[0]
    return SchedulingDecision(
        pod_name=pod.name,
        source_node=pod.node_name,
        target_node=node.name,
        policy=policy,
        score=score,
        reason="highest normalized residual capacity",
    )
