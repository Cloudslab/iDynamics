"""Application-generality metric schema and row utilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from idynamics.gda.metrics import pod_node_occupancy_ratio, sla_pressure


APPLICATION_POLICY_TIMESERIES_COLUMNS = [
    "benchmark",
    "run_id",
    "namespace",
    "scale",
    "replica_level",
    "replica_config",
    "workload_mode",
    "repeat",
    "policy",
    "policy_display_name",
    "step",
    "time_s",
    "evidence_type",
    "request_type",
    "traffic_stress",
    "weighted_edge_distance",
    "active_edge_count",
    "request_mix_entropy",
    "top3_hotspot_churn",
    "traffic_stress_gini",
    "traffic_stress_skew",
    "migration_count",
    "policy_decision_time_ms",
    "gda_query_latency_ms",
    "gda_build_time_ms",
    "gda_total_time_ms",
    "gda_nodes",
    "gda_edges",
    "gda_query_count",
    "latency_ms",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "throughput_rps",
    "error_rate",
    "sla_ms",
    "sla_pressure",
    "sla_violation_ratio",
    "worker_nodes_selected",
    "actual_app_pods",
    "ready_app_pods",
    "non_empty_worker_nodes",
    "pod_node_occupancy_ratio",
    "pod_restarts",
    "total_pods",
    "cluster_cpu_utilization",
    "cluster_memory_utilization",
    "top_node_cpu_utilization",
]

USER_REQUESTED_POLICY_COLUMNS = [
    "policy",
    "policy_display_name",
    "step",
    "time_s",
    "evidence_type",
    "traffic_stress",
    "weighted_edge_distance",
    "active_edge_count",
    "request_mix_entropy",
    "top3_hotspot_churn",
    "traffic_stress_gini",
    "traffic_stress_skew",
    "migration_count",
    "policy_decision_time_ms",
    "latency_ms",
    "sla_ms",
    "sla_pressure",
    "sla_violation_ratio",
]


@dataclass(frozen=True)
class ApplicationRunContext:
    benchmark: str
    run_id: str
    namespace: str
    scale: str
    replica_level: str = ""
    replica_config: str = ""
    workload_mode: str = ""
    repeat: str | int = ""
    request_type: str = "mixed"
    worker_nodes_selected: int | str = ""
    actual_app_pods: int | str = ""
    ready_app_pods: int | str = ""
    non_empty_worker_nodes: int | str = ""
    pod_restarts: int | str = ""
    total_pods: int | str = ""
    cluster_cpu_utilization: float | str = ""
    cluster_memory_utilization: float | str = ""
    top_node_cpu_utilization: float | str = ""

    @property
    def occupancy_ratio(self) -> float | str:
        try:
            return pod_node_occupancy_ratio(int(self.non_empty_worker_nodes), int(self.worker_nodes_selected))
        except (TypeError, ValueError):
            return ""


def _fmt(value: object) -> object:
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


def build_application_policy_row(
    policy_row: Mapping[str, object],
    context: ApplicationRunContext,
    *,
    gda_metrics: Mapping[str, object] | None = None,
    latency_distribution: Mapping[str, object] | None = None,
    throughput_rps: float | str = "",
    error_rate: float | str = "",
) -> dict[str, object]:
    """Return one row matching APPLICATION_POLICY_TIMESERIES_COLUMNS."""

    gda = gda_metrics or {}
    distribution = latency_distribution or {}
    latency_ms = policy_row.get("latency_ms", "")
    sla_ms = policy_row.get("sla_ms", "")
    pressure = policy_row.get("sla_pressure", "")
    if pressure == "" and latency_ms != "" and sla_ms != "":
        pressure = sla_pressure(float(latency_ms), float(sla_ms))

    row: dict[str, object] = {
        "benchmark": context.benchmark,
        "run_id": context.run_id,
        "namespace": context.namespace,
        "scale": context.scale,
        "replica_level": context.replica_level,
        "replica_config": context.replica_config,
        "workload_mode": context.workload_mode,
        "repeat": context.repeat,
        "request_type": context.request_type,
        "gda_query_latency_ms": gda.get("gda_query_latency_ms", ""),
        "gda_build_time_ms": gda.get("gda_build_time_ms", ""),
        "gda_total_time_ms": gda.get("gda_total_time_ms", ""),
        "gda_nodes": gda.get("gda_nodes", ""),
        "gda_edges": gda.get("gda_edges", policy_row.get("active_edge_count", "")),
        "gda_query_count": gda.get("gda_query_count", ""),
        "p50_ms": distribution.get("p50_ms", latency_ms),
        "p95_ms": distribution.get("p95_ms", latency_ms),
        "p99_ms": distribution.get("p99_ms", latency_ms),
        "throughput_rps": throughput_rps,
        "error_rate": error_rate,
        "worker_nodes_selected": context.worker_nodes_selected,
        "actual_app_pods": context.actual_app_pods,
        "ready_app_pods": context.ready_app_pods,
        "non_empty_worker_nodes": context.non_empty_worker_nodes,
        "pod_node_occupancy_ratio": context.occupancy_ratio,
        "pod_restarts": context.pod_restarts,
        "total_pods": context.total_pods,
        "cluster_cpu_utilization": context.cluster_cpu_utilization,
        "cluster_memory_utilization": context.cluster_memory_utilization,
        "top_node_cpu_utilization": context.top_node_cpu_utilization,
        **{column: policy_row.get(column, "") for column in USER_REQUESTED_POLICY_COLUMNS},
        "sla_pressure": pressure,
    }
    return {column: _fmt(row.get(column, "")) for column in APPLICATION_POLICY_TIMESERIES_COLUMNS}


def validate_application_policy_columns(columns: list[str]) -> None:
    if columns != APPLICATION_POLICY_TIMESERIES_COLUMNS:
        raise ValueError("application_policy_timeseries.csv columns do not match the required schema")
