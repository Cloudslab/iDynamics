from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = [
    "social-network",
    "online-boutique",
    "moe-serving",
    "deathstar-hotel",
    "train-ticket",
    "sock-shop",
]
REQUIRED_FILES = [
    "README.md",
    "metadata.yaml",
    "adapter/service_map.yaml",
    "adapter/workload_mix.yaml",
    "adapter/replica_profiles.yaml",
    "scripts/fetch.sh",
    "scripts/deploy.sh",
    "scripts/smoke.sh",
    "scripts/load.sh",
    "scripts/collect.sh",
    "scripts/cleanup.sh",
    "scripts/reproduce.sh",
]
PINNED_COMMITS = {
    "social-network": "6ecb09706140f8730b5385c08f1386c654c3c526",
    "online-boutique": "5096a85b2f3bf41bef53363cfe5478d5b86ac701",
    "deathstar-hotel": "6ecb09706140f8730b5385c08f1386c654c3c526",
    "train-ticket": "313886e99befb94be6cd45f085c98e0019f59829",
    "sock-shop": "9dff06fae4981921caec6a62393a6ebfce4b3e3f",
}


def test_benchmark_folder_contract() -> None:
    for benchmark in BENCHMARKS:
        root = REPO_ROOT / "benchmarks" / benchmark
        for relative in REQUIRED_FILES:
            assert (root / relative).exists(), f"{benchmark} missing {relative}"


def test_third_party_metadata_pins_commit_and_license() -> None:
    for benchmark, commit in PINNED_COMMITS.items():
        metadata = (REPO_ROOT / "benchmarks" / benchmark / "metadata.yaml").read_text()
        assert commit in metadata
        assert "Apache-2.0" in metadata
        assert "vendored: false" in metadata


def test_moe_metadata_is_cpu_only() -> None:
    metadata = (REPO_ROOT / "benchmarks" / "moe-serving" / "metadata.yaml").read_text()
    readme = (REPO_ROOT / "benchmarks" / "moe-serving" / "README.md").read_text()
    assert "cpu_only: true" in metadata
    assert "gpu_required: false" in metadata
    assert "CPU-only" in readme


def test_benchmark_scripts_have_help_and_valid_bash() -> None:
    for benchmark in BENCHMARKS:
        scripts_dir = REPO_ROOT / "benchmarks" / benchmark / "scripts"
        for script in ["fetch", "deploy", "smoke", "load", "collect", "cleanup", "reproduce"]:
            path = scripts_dir / f"{script}.sh"
            subprocess.run(["bash", "-n", str(path)], check=True)
            result = subprocess.run(
                [str(path), "--help"],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            assert "Usage:" in result.stdout
            assert "--namespace" in result.stdout
