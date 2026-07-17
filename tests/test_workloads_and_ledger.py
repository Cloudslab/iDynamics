from pathlib import Path

from idynamics.ledger.run import init_run_ledger, log_command, validate_run_ledger
from idynamics.workloads.moe import default_placement, idynamics_placement, placement_cost, policy_placement, traffic_edges, weights_for_step
from idynamics.workloads.social import WorkloadMixer, default_online_boutique_requests


def test_workload_mixer_probabilities_sum_to_one() -> None:
    mixer = WorkloadMixer(["read", "write", "search"], "sinusoidal", steps=8, interval_s=1.0, seed=7)

    for probabilities in mixer.schedule():
        assert set(probabilities) == {"read", "write", "search"}
        assert abs(sum(probabilities.values()) - 1.0) < 1e-9


def test_workload_mixer_modes_keep_overlapping_requests(tmp_path: Path) -> None:
    names = ["read", "write", "search"]
    trace = tmp_path / "mix.csv"
    trace.write_text("step,p_read,p_write,p_search\n0,0.2,0.3,0.5\n1,0.4,0.4,0.2\n")

    for mode in ("step", "linear", "sinusoidal", "markov"):
        mixer = WorkloadMixer(names, mode, steps=6, interval_s=1.0, seed=7)
        assert all(sum(1 for value in probabilities.values() if value > 0.0) >= 2 for probabilities in mixer.schedule())

    csv_mixer = WorkloadMixer(names, "trace_csv", steps=3, interval_s=1.0, seed=7, trace_csv=trace)
    assert csv_mixer.probabilities(0) == {"read": 0.2, "write": 0.3, "search": 0.5}
    assert csv_mixer.probabilities(2) == {"read": 0.4, "write": 0.4, "search": 0.2}


def test_workload_mixer_online_boutique_defaults_and_artifacts(tmp_path: Path) -> None:
    mixer = WorkloadMixer(workload_mode="online-boutique", mode="linear", steps=200, interval_s=5.0, qps=95.0, seed=13)
    expected = ["index", "setCurrency", "browseProduct", "addToCart", "viewCart", "checkout"]
    assert mixer.request_names == expected
    assert [request.default_weight for request in default_online_boutique_requests()] == [1.0, 2.0, 10.0, 2.0, 3.0, 1.0]

    row = mixer.request_mix_rows()[0]
    assert row["time_s"] == "0.000"
    assert abs(sum(float(row[f"qps_{name}"]) for name in expected) - 95.0) < 1e-5
    assert "request_mix_entropy" in row

    mixer.write_artifacts(tmp_path)
    assert (tmp_path / "workload_mixer_modes.csv").read_text().splitlines()[0] == "mode,step,p_index,p_setCurrency,p_browseProduct,p_addToCart,p_viewCart,p_checkout"
    header = (tmp_path / "request_mix_timeseries.csv").read_text().splitlines()[0]
    assert header.startswith("step,time_s,p_index,p_setCurrency,p_browseProduct")
    assert "qps_checkout" in header
    assert "sla_violation_ratio" in header


def test_workload_mixer_moe_modes_and_horizons() -> None:
    expected = [
        "single_expert",
        "multi_expert_top2",
        "multi_expert_top4",
        "cache_hit",
        "cache_miss",
        "payload_small",
        "payload_large",
        "batch_small",
        "batch_large",
    ]
    for mode in ("step", "linear", "sinusoidal", "markov"):
        for steps in (200, 500, 1000):
            mixer = WorkloadMixer(workload_mode="moe-serving", mode=mode, steps=steps, interval_s=5.0, qps=120.0, seed=17)
            schedule = mixer.schedule()
            assert mixer.request_names == expected
            assert len(schedule) == steps
            assert all(set(row) == set(expected) for row in schedule)
            assert all(abs(sum(row.values()) - 1.0) < 1e-9 for row in schedule)


def test_moe_idynamics_placement_reduces_or_matches_hot_path_cost() -> None:
    weights = weights_for_step(experts=4, step=0, total_steps=10, mode="stable", alpha=1.2)
    edges = traffic_edges(weights, requests=100, top_k=2, payload_bytes=256)

    default_cost = placement_cost(edges, default_placement(experts=4, nodes=3))
    idynamics_cost = placement_cost(edges, idynamics_placement(experts=4, nodes=3, weights=weights, top_k=2))

    assert idynamics_cost <= default_cost


def test_moe_policy_placements_cover_policy2_policy3_policy4() -> None:
    weights = weights_for_step(experts=6, step=3, total_steps=12, mode="phase-shift", alpha=1.2)

    placements = {policy: policy_placement(policy, experts=6, nodes=5, weights=weights, top_k=2) for policy in ("policy2", "policy3", "policy4")}

    assert placements["policy2"]["frontend"] == placements["policy2"]["router"]
    assert placements["policy3"]["router"] == placements["policy3"]["aggregator"]
    assert placements["policy3"]["frontend"] != placements["policy3"]["router"]
    assert placements["policy4"]["cache"] != placements["policy4"]["router"]


def test_init_run_ledger_creates_required_artifacts(tmp_path: Path) -> None:
    (tmp_path / "experiments" / "runs").mkdir(parents=True)
    ledger = init_run_ledger("unit-ledger", purpose="unit_test", root=tmp_path, extra_config={"nodes": 2})

    validate_run_ledger(ledger.root)
    log_command(ledger, "python -m pytest")

    assert ledger.config_path.read_text().splitlines()[0] == "run_id: unit-ledger"
    assert "python -m pytest" in ledger.commands_log.read_text()
