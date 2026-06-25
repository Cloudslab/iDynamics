from __future__ import annotations

import csv
import os
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from idynamics.workloads.social import WorkloadMixer
from idynamics.gda.application_metrics import APPLICATION_POLICY_TIMESERIES_COLUMNS


SCRIPT = Path("scripts/experiments/continuous_callgraph.py")
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_continuous_callgraph_module():
    spec = importlib.util.spec_from_file_location("continuous_callgraph", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mode", ["step", "linear", "sinusoidal", "markov"])
@pytest.mark.parametrize("steps", [200, 500, 1000])
def test_workload_mixer_supports_longmix_horizons(mode: str, steps: int) -> None:
    mixer = WorkloadMixer(["read_home", "compose_post", "read_user"], mode, steps, interval_s=1.0, seed=11)
    schedule = mixer.schedule()
    assert len(schedule) == steps
    assert all(abs(sum(row.values()) - 1.0) < 1e-9 for row in schedule)
    assert all(set(row) == {"read_home", "compose_post", "read_user"} for row in schedule)


def test_graph_metric_helpers_are_bounded() -> None:
    module = load_continuous_callgraph_module()
    previous_edges = {("a", "b"): 10.0, ("b", "c"): 5.0}
    edges = {("a", "b"): 8.0, ("c", "d"): 12.0, ("d", "e"): 2.0}
    assert 0.0 <= module.request_mix_entropy({"a": 0.5, "b": 0.25, "c": 0.25}) <= 2.0
    assert 0.0 <= module.gini(list(edges.values())) <= 1.0
    assert module.skewness([1.0, 2.0, 10.0]) > 0.0
    assert 0.0 <= module.hotspot_churn(previous_edges, edges, k=2) <= 1.0
    assert module.normalize_policy_labels("kubernetes,policy1,policy4") == ["kubernetes-default", "cga", "hda"]


def test_continuous_callgraph_writes_longmix_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "continuous-longmix-test"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else str(REPO_ROOT)
    subprocess.run(
        [
            sys.executable,
            str((REPO_ROOT / SCRIPT).resolve()),
            "--run-dir",
            str(run_dir),
            "--mode",
            "sinusoidal",
            "--steps",
            "12",
            "--interval-s",
            "0.1",
            "--policies",
            "kubernetes,policy1,policy4",
        ],
        check=True,
        env=env,
        cwd=tmp_path,
    )

    required = [
        "raw/request_mix_timeseries.csv",
        "raw/callgraph_snapshots.csv",
        "raw/callgraph_snapshots.jsonl",
        "raw/policy_replay_timeseries.csv",
        "raw/e2e_policy_timeseries.csv",
        "raw/application_policy_timeseries.csv",
        "processed/continuous_graph_metrics.json",
        "processed/policy_e2e_summary.csv",
        "figures/figure_manifest.json",
    ]
    for relative_path in required:
        assert (run_dir / relative_path).exists(), relative_path

    with (run_dir / "raw/request_mix_timeseries.csv").open(newline="") as input_file:
        rows = list(csv.DictReader(input_file))
    assert len(rows) == 12
    for field in [
        "request_mix_entropy",
        "top3_hotspot_churn",
        "active_edge_count",
        "traffic_stress_gini",
        "traffic_stress_skew",
        "migration_count",
        "policy_decision_time_ms",
    ]:
        assert field in rows[0]

    with (run_dir / "raw/policy_replay_timeseries.csv").open(newline="") as input_file:
        policy_rows = list(csv.DictReader(input_file))
    assert {row["policy"] for row in policy_rows} == {"kubernetes-default", "cga", "hda"}
    assert {row["evidence_type"] for row in policy_rows} == {"replay"}

    with (run_dir / "raw/application_policy_timeseries.csv").open(newline="") as input_file:
        reader = csv.DictReader(input_file)
        application_rows = list(reader)
    assert reader.fieldnames == APPLICATION_POLICY_TIMESERIES_COLUMNS
    assert len(application_rows) == 36
    assert application_rows[0]["benchmark"] == "social-network"
    assert application_rows[0]["scale"] == "synthetic"
    assert application_rows[0]["throughput_rps"] == "90.000000"
    assert application_rows[0]["gda_edges"] == application_rows[0]["active_edge_count"]

    metrics = json.loads((run_dir / "processed/continuous_graph_metrics.json").read_text())
    assert metrics["policy_latency_evidence_type"] == "replay"
    assert metrics["mean_request_mix_entropy"] > 0.0
