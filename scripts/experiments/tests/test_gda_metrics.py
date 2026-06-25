import pytest

from idynamics.gda.sparse import (
    build_graph_from_traffic_edges,
    build_sparse_prometheus_queries,
    legacy_dense_query_count,
    sparse_query_count,
    traffic_edges_from_prometheus_series,
)
from idynamics.gda.application_metrics import (
    APPLICATION_POLICY_TIMESERIES_COLUMNS,
    USER_REQUESTED_POLICY_COLUMNS,
    ApplicationRunContext,
    build_application_policy_row,
    validate_application_policy_columns,
)
from idynamics.gda.metrics import (
    active_edge_count,
    edge_jaccard_distance,
    gini,
    graph_change_rate,
    hot_edge_rank_correlation,
    pod_node_occupancy_ratio,
    request_mix_entropy,
    skewness,
    sla_pressure,
    sla_violation_ratio,
    top_hotspot_churn,
    traffic_stress,
    weighted_edge_distance,
)
from idynamics.types import TrafficEdge


def test_graph_distances_are_zero_for_identical_edges() -> None:
    previous = {("a", "b"): 10.0, ("b", "c"): 5.0}
    current = dict(previous)

    assert edge_jaccard_distance(previous, current) == 0.0
    assert weighted_edge_distance(previous, current) == 0.0
    assert graph_change_rate(previous, current, interval_s=5.0) == 0.0
    assert hot_edge_rank_correlation(previous, current) == pytest.approx(1.0)


def test_weighted_edge_distance_accounts_for_changed_weights_and_edges() -> None:
    previous = {("a", "b"): 10.0, ("b", "c"): 5.0}
    current = {("a", "b"): 5.0, ("c", "d"): 15.0}

    assert edge_jaccard_distance(previous, current) == 1.0 - (1.0 / 3.0)
    assert weighted_edge_distance(previous, current) == 25.0 / 30.0
    assert graph_change_rate(previous, current, interval_s=2.0) == (25.0 / 30.0) / 2.0


def test_application_generality_metric_formulas_are_bounded() -> None:
    previous = {("a", "b"): 10.0, ("b", "c"): 5.0}
    current = {("a", "b"): 8.0, ("c", "d"): 12.0, ("d", "e"): 2.0}

    assert traffic_stress(current) == 22.0
    assert active_edge_count(current) == 3
    assert active_edge_count(current, threshold=8.0) == 1
    assert request_mix_entropy({"read": 0.5, "write": 0.25, "browse": 0.25}) == pytest.approx(1.5)
    assert 0.0 <= top_hotspot_churn(previous, current, k=2) <= 1.0
    assert 0.0 <= gini(current.values()) <= 1.0
    assert skewness([1.0, 2.0, 10.0]) > 0.0
    assert sla_pressure(180.0, 150.0) == pytest.approx(1.2)
    assert sla_violation_ratio(180.0, 150.0) == pytest.approx(0.2)
    assert pod_node_occupancy_ratio(7, 10) == pytest.approx(0.7)


def test_application_policy_timeseries_schema_builder() -> None:
    context = ApplicationRunContext(
        benchmark="online-boutique",
        run_id="run-1",
        namespace="boutique",
        scale="scale45",
        replica_level="replica5",
        replica_config="frontend=5",
        workload_mode="markov",
        repeat=2,
        worker_nodes_selected=45,
        actual_app_pods=52,
        ready_app_pods=52,
        non_empty_worker_nodes=38,
        pod_restarts=0,
        total_pods=55,
    )
    policy_row = {
        "policy": "cga",
        "policy_display_name": "CGA",
        "step": 3,
        "time_s": "15.000",
        "evidence_type": "live/application",
        "traffic_stress": "900.0",
        "weighted_edge_distance": "0.25",
        "active_edge_count": "17",
        "request_mix_entropy": "1.5",
        "top3_hotspot_churn": "0.5",
        "traffic_stress_gini": "0.3",
        "traffic_stress_skew": "0.9",
        "migration_count": "4",
        "policy_decision_time_ms": "8.4",
        "latency_ms": "120.0",
        "sla_ms": "150.0",
        "sla_violation_ratio": "0.0",
    }

    row = build_application_policy_row(
        policy_row,
        context,
        gda_metrics={"gda_query_latency_ms": "10.0", "gda_build_time_ms": "3.0", "gda_total_time_ms": "13.0", "gda_nodes": "12", "gda_edges": "17", "gda_query_count": "2"},
        latency_distribution={"p50_ms": "100.0", "p95_ms": "140.0", "p99_ms": "180.0"},
        throughput_rps="200.0",
        error_rate="0.01",
    )

    assert list(row) == APPLICATION_POLICY_TIMESERIES_COLUMNS
    assert all(column in row for column in USER_REQUESTED_POLICY_COLUMNS)
    assert row["pod_node_occupancy_ratio"] == "0.844444"
    assert row["sla_pressure"] == "0.800000"
    validate_application_policy_columns(APPLICATION_POLICY_TIMESERIES_COLUMNS)
    with pytest.raises(ValueError):
        validate_application_policy_columns(APPLICATION_POLICY_TIMESERIES_COLUMNS[:-1])


def test_sparse_gda_merges_aggregate_prometheus_edges() -> None:
    sent = [
        {"metric": {"source_workload": "frontend", "destination_workload": "cart"}, "value": [0, "100"]},
        {"metric": {"source_workload": "frontend", "destination_workload": "cart"}, "value": [0, "50"]},
    ]
    received = [
        {"metric": {"source_workload": "frontend", "destination_workload": "cart"}, "value": [0, "70"]},
        {"metric": {"source_workload": "cart", "destination_workload": "db"}, "value": [0, "30"]},
    ]

    edges = traffic_edges_from_prometheus_series(sent, received)

    assert edges == [
        TrafficEdge(source="cart", destination="db", sent_bytes_per_s=0.0, received_bytes_per_s=30.0),
        TrafficEdge(source="frontend", destination="cart", sent_bytes_per_s=150.0, received_bytes_per_s=70.0),
    ]


def test_sparse_graph_filters_inactive_and_out_of_scope_edges() -> None:
    graph = build_graph_from_traffic_edges(
        ["frontend", "cart"],
        [
            TrafficEdge(source="frontend", destination="cart", sent_bytes_per_s=100.0, received_bytes_per_s=100.0),
            TrafficEdge(source="cart", destination="frontend", sent_bytes_per_s=1.0, received_bytes_per_s=1.0),
            TrafficEdge(source="frontend", destination="unknown", sent_bytes_per_s=100.0),
        ],
        min_stress_bytes=10.0,
    )

    assert graph.number_of_edges() == 1
    assert ("frontend", "cart") in graph.edges


def test_gda_query_counts_keep_dense_pairwise_behind_explicit_comparison() -> None:
    assert sparse_query_count() == 2
    assert legacy_dense_query_count(1000) == 1_998_000
    sent_query, received_query = build_sparse_prometheus_queries("shop", window="5m")
    assert "sum by (source_workload, destination_workload)" in sent_query
    assert 'source_workload_namespace="shop"' in sent_query
    assert "istio_tcp_received_bytes_total" in received_query
