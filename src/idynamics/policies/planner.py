"""Executable placement policies for iDynamics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from idynamics.types import NetworkMatrix, NodeInfo, PodInfo, SchedulingDecision, ServiceGraph, TrafficEdge


@dataclass(frozen=True)
class PlacementPlan:
    """Auditable policy output for CLI and experiment integration."""

    policy: str
    decisions: tuple[SchedulingDecision, ...]
    placement: Mapping[str, str]
    objective_cost: float


def _service(pod: PodInfo) -> str:
    return pod.service or pod.labels.get("component") or pod.name


def _network_index(network: NetworkMatrix | None) -> dict[str, int]:
    if network is None:
        return {}
    return {name: idx for idx, name in enumerate(network.node_names)}


def _latency(network: NetworkMatrix | None, index: Mapping[str, int], source: str, target: str) -> float:
    if source == target:
        return 0.05
    if network is None or source not in index or target not in index:
        return 1.0
    return max(0.05, network.latency_ms[index[source]][index[target]])


def _bandwidth(network: NetworkMatrix | None, index: Mapping[str, int], source: str, target: str) -> float:
    if source == target:
        return 1000000.0
    if network is None or source not in index or target not in index:
        return 1000.0
    return max(0.001, network.bandwidth_mbps[index[source]][index[target]])


def _edge_lookup(graph: ServiceGraph | None) -> dict[tuple[str, str], TrafficEdge]:
    if graph is None:
        return {}
    return {(edge.source, edge.destination): edge for edge in graph.edges}


def _normalize(value: float, maximum: float) -> float:
    return value / max(1.0, maximum)


class BasePlacementPolicy:
    """Greedy capacity-aware planner shared by the built-in policies."""

    name = "base"

    def edge_cost(
        self,
        edge: TrafficEdge,
        source_node: str,
        target_node: str,
        network: NetworkMatrix | None,
        network_index: Mapping[str, int],
        maxima: Mapping[str, float],
    ) -> float:
        raise NotImplementedError

    def plan(
        self,
        pods: list[PodInfo] | tuple[PodInfo, ...],
        nodes: list[NodeInfo] | tuple[NodeInfo, ...],
        service_graph: ServiceGraph | None = None,
        network: NetworkMatrix | None = None,
    ) -> list[SchedulingDecision]:
        return list(self.plan_with_details(pods, nodes, service_graph, network).decisions)

    def plan_with_details(
        self,
        pods: list[PodInfo] | tuple[PodInfo, ...],
        nodes: list[NodeInfo] | tuple[NodeInfo, ...],
        service_graph: ServiceGraph | None = None,
        network: NetworkMatrix | None = None,
    ) -> PlacementPlan:
        if not pods:
            return PlacementPlan(self.name, tuple(), {}, 0.0)
        ready_nodes = [node for node in nodes if node.ready]
        if not ready_nodes:
            raise ValueError("no ready nodes available")

        edges = tuple(service_graph.edges if service_graph else ())
        edge_by_pair = _edge_lookup(service_graph)
        network_index = _network_index(network)
        maxima = {
            "request_rate": max((edge.request_rate for edge in edges), default=1.0),
            "payload": max((edge.sent_bytes_per_s + edge.received_bytes_per_s for edge in edges), default=1.0),
            "stress": max((edge.stress_bytes_per_s for edge in edges), default=1.0),
            "edge_latency": max(((edge.latency_ms or 0.0) for edge in edges), default=1.0),
        }

        fixed: dict[str, str] = {}
        remaining: list[PodInfo] = []
        cpu_used = {node.name: node.cpu_allocated_millicores for node in ready_nodes}
        mem_used = {node.name: node.memory_allocated_mib for node in ready_nodes}
        node_by_name = {node.name: node for node in ready_nodes}

        for pod in pods:
            service = _service(pod)
            locked = pod.labels.get("idynamics.io/locked") == "true"
            if locked and pod.node_name:
                if pod.node_name not in node_by_name:
                    raise ValueError(f"locked pod {pod.name} references non-ready node {pod.node_name}")
                fixed[service] = pod.node_name
                cpu_used[pod.node_name] += pod.cpu_request_millicores
                mem_used[pod.node_name] += pod.memory_request_mib
            else:
                remaining.append(pod)

        def service_priority(pod: PodInfo) -> float:
            service = _service(pod)
            value = 0.0
            for edge in edges:
                if edge.source == service or edge.destination == service:
                    value += self._priority_weight(edge, maxima)
            return value

        placement = dict(fixed)
        decisions: list[SchedulingDecision] = []
        for pod in sorted(remaining, key=lambda item: (-service_priority(item), _service(item), item.name)):
            service = _service(pod)
            candidates: list[tuple[float, str, str]] = []
            for node in ready_nodes:
                cpu_after = cpu_used[node.name] + pod.cpu_request_millicores
                mem_after = mem_used[node.name] + pod.memory_request_mib
                if cpu_after > node.cpu_capacity_millicores or mem_after > node.memory_capacity_mib:
                    continue
                candidate = dict(placement)
                candidate[service] = node.name
                cost = self._partial_cost(candidate, edge_by_pair, network, network_index, maxima)
                residual_cpu = (node.cpu_capacity_millicores - cpu_after) / max(1.0, node.cpu_capacity_millicores)
                residual_mem = (node.memory_capacity_mib - mem_after) / max(1.0, node.memory_capacity_mib)
                score = cost - 0.001 * min(residual_cpu, residual_mem)
                candidates.append((score, node.name, f"partial objective cost {cost:.6f}"))
            if not candidates:
                raise ValueError(f"no feasible node for pod {pod.namespace}/{pod.name}")
            _, target_node, reason = min(candidates, key=lambda item: (item[0], item[1]))
            placement[service] = target_node
            cpu_used[target_node] += pod.cpu_request_millicores
            mem_used[target_node] += pod.memory_request_mib
            objective = self._partial_cost(placement, edge_by_pair, network, network_index, maxima)
            decisions.append(
                SchedulingDecision(
                    pod_name=pod.name,
                    source_node=pod.node_name,
                    target_node=target_node,
                    policy=self.name,
                    score=-objective,
                    reason=reason,
                )
            )
        return PlacementPlan(self.name, tuple(decisions), placement, self._partial_cost(placement, edge_by_pair, network, network_index, maxima))

    def _priority_weight(self, edge: TrafficEdge, maxima: Mapping[str, float]) -> float:
        return edge.stress_bytes_per_s

    def _partial_cost(
        self,
        placement: Mapping[str, str],
        edge_by_pair: Mapping[tuple[str, str], TrafficEdge],
        network: NetworkMatrix | None,
        network_index: Mapping[str, int],
        maxima: Mapping[str, float],
    ) -> float:
        total = 0.0
        for (source, target), edge in edge_by_pair.items():
            if source not in placement or target not in placement:
                continue
            total += self.edge_cost(edge, placement[source], placement[target], network, network_index, maxima)
        return total


class Policy1TrafficAffinity(BasePlacementPolicy):
    """CGA: co-locate high-stress call-graph edges."""

    name = "policy1-callgraph-traffic-affinity"

    def edge_cost(self, edge: TrafficEdge, source_node: str, target_node: str, network: NetworkMatrix | None, network_index: Mapping[str, int], maxima: Mapping[str, float]) -> float:
        if source_node == target_node:
            return 0.0
        return _normalize(edge.stress_bytes_per_s, maxima["stress"])


class Policy2LatencyCriticalPath(BasePlacementPolicy):
    """Auxiliary latency-critical-path planner."""

    name = "policy2-latency-critical-path"

    def _priority_weight(self, edge: TrafficEdge, maxima: Mapping[str, float]) -> float:
        return _normalize(edge.request_rate, maxima["request_rate"]) + _normalize(edge.latency_ms or 0.0, maxima["edge_latency"])

    def edge_cost(self, edge: TrafficEdge, source_node: str, target_node: str, network: NetworkMatrix | None, network_index: Mapping[str, int], maxima: Mapping[str, float]) -> float:
        edge_priority = 0.65 * _normalize(edge.request_rate, maxima["request_rate"]) + 0.35 * _normalize(edge.latency_ms or 0.0, maxima["edge_latency"])
        return edge_priority * _latency(network, network_index, source_node, target_node)


class Policy3BandwidthPayloadAware(BasePlacementPolicy):
    """Auxiliary bandwidth-payload-aware planner."""

    name = "policy3-bandwidth-payload-aware"

    def _priority_weight(self, edge: TrafficEdge, maxima: Mapping[str, float]) -> float:
        return _normalize(edge.sent_bytes_per_s + edge.received_bytes_per_s, maxima["payload"])

    def edge_cost(self, edge: TrafficEdge, source_node: str, target_node: str, network: NetworkMatrix | None, network_index: Mapping[str, int], maxima: Mapping[str, float]) -> float:
        payload = _normalize(edge.sent_bytes_per_s + edge.received_bytes_per_s, maxima["payload"])
        return payload / _bandwidth(network, network_index, source_node, target_node)


class Policy4HybridDynamics(BasePlacementPolicy):
    """HDA: combine traffic stress, latency, and bandwidth."""

    name = "policy4-hybrid-dynamics"

    def _priority_weight(self, edge: TrafficEdge, maxima: Mapping[str, float]) -> float:
        return _normalize(edge.stress_bytes_per_s, maxima["stress"]) + _normalize(edge.sent_bytes_per_s + edge.received_bytes_per_s, maxima["payload"])

    def edge_cost(self, edge: TrafficEdge, source_node: str, target_node: str, network: NetworkMatrix | None, network_index: Mapping[str, int], maxima: Mapping[str, float]) -> float:
        stress = _normalize(edge.stress_bytes_per_s, maxima["stress"])
        payload = _normalize(edge.sent_bytes_per_s + edge.received_bytes_per_s, maxima["payload"])
        delay = _latency(network, network_index, source_node, target_node)
        bandwidth = _bandwidth(network, network_index, source_node, target_node)
        return 0.55 * stress * delay + 0.45 * payload / bandwidth


POLICIES = {
    "policy1": Policy1TrafficAffinity,
    "p1": Policy1TrafficAffinity,
    "policy2": Policy2LatencyCriticalPath,
    "p2": Policy2LatencyCriticalPath,
    "policy3": Policy3BandwidthPayloadAware,
    "p3": Policy3BandwidthPayloadAware,
    "policy4": Policy4HybridDynamics,
    "p4": Policy4HybridDynamics,
}


def make_policy(name: str) -> BasePlacementPolicy:
    try:
        return POLICIES[name.lower()]()
    except KeyError as exc:
        raise ValueError(f"unknown policy {name!r}; expected one of policy1, policy2, policy3, policy4") from exc
