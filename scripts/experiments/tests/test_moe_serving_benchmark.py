from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from idynamics.workloads.moe import weights_for_step
from iDynamicsPackagesModules.Evaluations.workload_mixer import WorkloadMixer, default_moe_requests


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_moe_weights_support_phase_shift_alias_and_markov() -> None:
    hyphen = weights_for_step(6, 3, 24, "phase-shift", 1.2)
    underscore = weights_for_step(6, 3, 24, "phase_shift", 1.2)
    markov_early = weights_for_step(6, 3, 24, "markov", 1.2)
    markov_late = weights_for_step(6, 16, 24, "markov", 1.2)

    assert hyphen == underscore
    assert abs(sum(markov_early) - 1.0) < 1e-9
    assert markov_early != markov_late


def test_workload_dry_run_outputs_latency_and_sla_summary(tmp_path: Path) -> None:
    csv_path = tmp_path / "load.csv"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "examples/moe-serving/workload/generate_load.py"),
            "--dry-run",
            "--requests",
            "12",
            "--experts",
            "4",
            "--skew-mode",
            "cache_stress",
            "--request-type",
            "mixed",
            "--output",
            str(csv_path),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    summary = json.loads(result.stdout)
    assert summary["requests"] == 12
    assert "p50_latency_ms" in summary
    assert "p99_latency_ms" in summary
    assert "throughput_rps" in summary
    assert "sla_violations" in summary
    header = csv_path.read_text().splitlines()[0].split(",")
    assert header[:4] == ["request_id", "request_type", "status", "latency_ms"]
    assert {"top_k", "payload_bytes", "batch_size", "cache_intent"}.issubset(header)


def test_moe_request_types_and_optional_modes_are_first_class() -> None:
    request_names = [request.name for request in default_moe_requests()]
    assert request_names == [
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
    for mode in ["step", "linear", "sinusoidal", "markov", "expert_skew_shift", "cache_stress", "payload_heavy"]:
        mixer = WorkloadMixer(request_names, mode=mode, steps=12, workload_mode="moe-serving")
        schedule = mixer.schedule()
        assert len(schedule) == 12
        assert all(abs(sum(row.values()) - 1.0) < 1e-9 for row in schedule)
        weights = weights_for_step(6, 3, 12, mode, 1.2)
        assert abs(sum(weights) - 1.0) < 1e-9


def test_manifest_renderer_accepts_cga_hda_aliases(tmp_path: Path) -> None:
    output = tmp_path / "moe.yaml"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "examples/moe-serving/k8s/render_manifests.py"),
            "--experts",
            "3",
            "--policy",
            "hda",
            "--node-pool-label",
            "idynamics.dev/scale10=true",
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    rendered = output.read_text()
    assert "idynamics.io/policy: policy4" in rendered
    assert "resources:" in rendered
    assert "idynamics.dev/scale10: \"true\"" in rendered


def test_physical_runner_policy_aliases() -> None:
    runner = load_module(REPO_ROOT / "scripts/experiments/run_physical_moe_k8s.py", "run_physical_moe_k8s")
    assert runner.manifest_policy("cga") == "policy1"
    assert runner.manifest_policy("hda") == "policy4"
    assert runner.manifest_policy("policy2-critical-path-latency") == "policy2"
    assert runner.scale_label("scale45") == "idynamics.dev/scale45"


def test_moe_longmix_replica_counts() -> None:
    runner = load_module(REPO_ROOT / "scripts/experiments/run_moe_longmix_replica.py", "run_moe_longmix_replica")
    counts = runner.replica_counts("replica3", 6)
    assert counts["expert_count"] == 6
    assert counts["replicas_per_expert"] == 3
    assert counts["router_replicas"] == 3
    assert counts["aggregator_replicas"] == 3
    assert counts["cache_replicas"] == 1
    assert counts["state_replicas"] == 1
    assert counts["total_app_pods"] == 31
