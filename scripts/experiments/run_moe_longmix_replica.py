#!/usr/bin/env python3
"""Run CPU-only MoE long-mix replay stages with replica/expert metadata."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from idynamics.workloads.moe import REQUEST_TYPES, weights_for_step


PROFILE_PATH = REPO_ROOT / "benchmarks" / "moe-serving" / "adapter" / "replica_profiles.yaml"
DEFAULT_POLICIES = "kubernetes-default,cga,hda,policy2,policy3"
STAGE_MATRIX = {
    "A": [("scale20", "replica3", "step", 200), ("scale20", "replica3", "linear", 200), ("scale20", "replica3", "sinusoidal", 200), ("scale20", "replica3", "markov", 200)],
    "B": [("scale45", "replica5", "step", 500), ("scale45", "replica5", "linear", 500), ("scale45", "replica5", "sinusoidal", 500), ("scale45", "replica5", "markov", 500)],
    "C": [
        ("scale20", "replica1", "sinusoidal", 500), ("scale20", "replica1", "markov", 500),
        ("scale20", "replica3", "sinusoidal", 500), ("scale20", "replica3", "markov", 500),
        ("scale20", "replica5", "sinusoidal", 500), ("scale20", "replica5", "markov", 500),
        ("scale45", "replica1", "sinusoidal", 500), ("scale45", "replica1", "markov", 500),
        ("scale45", "replica3", "sinusoidal", 500), ("scale45", "replica3", "markov", 500),
        ("scale45", "replica5", "sinusoidal", 500), ("scale45", "replica5", "markov", 500),
    ],
    "D": [("scale45", "replica5", "sinusoidal", 1000), ("scale45", "replica5", "markov", 1000)],
}


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sh(cmd: list[str], *, cwd: Path = REPO_ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else str(REPO_ROOT)
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=check)


def profile(level: str) -> dict[str, Any]:
    data = json.loads(PROFILE_PATH.read_text())
    return dict(data["replica_profiles"][level])


def replica_counts(level: str, experts: int) -> dict[str, int]:
    item = profile(level)
    stateless = int(item["stateless_replicas"])
    expert_replicas = int(item["expert_replicas"])
    router = int(item.get("router_replicas", stateless))
    aggregator = int(item.get("aggregator_replicas", stateless))
    cache = int(item.get("cache_replicas", 1))
    state = int(item.get("state_replicas", cache))
    total = stateless * 2 + router + aggregator + experts * expert_replicas + cache
    return {
        "expert_count": experts,
        "replicas_per_expert": expert_replicas,
        "router_replicas": router,
        "aggregator_replicas": aggregator,
        "cache_replicas": cache,
        "state_replicas": state,
        "total_app_pods": total,
    }


def replica_config(level: str, experts: int) -> str:
    counts = replica_counts(level, experts)
    return ";".join(f"{key}={counts[key]}" for key in sorted(counts))


def write_ledger_header(run_dir: Path, args: argparse.Namespace, stage: str, scale: str, replica_level: str, mode: str, steps: int) -> None:
    counts = replica_counts(replica_level, args.experts)
    config = {
        "run_id": run_dir.name,
        "created_utc": timestamp(),
        "purpose": "moe_longmix_replica_replay",
        "stage": stage,
        "benchmark": "moe-serving",
        "scale": scale,
        "replica_level": replica_level,
        "workload_mode": mode,
        "steps": steps,
        "interval_s": args.interval_s,
        "total_qps": args.total_qps,
        "experts": args.experts,
        "policies": args.policies,
        "evidence_type": "replay",
        "claim_boundary": "CPU-only MoE-style microbenchmark; no GPU-aware or production LLM-serving claim.",
        **counts,
    }
    run_dir.joinpath("config.yaml").write_text("\n".join(f"{key}: {value}" for key, value in config.items()) + "\n")
    run_dir.joinpath("git_sha.txt").write_text(sh(["git", "rev-parse", "HEAD"], check=False).stdout or "no-git-sha\n")
    run_dir.joinpath("git_status.txt").write_text(sh(["git", "status", "--short", "--branch"], check=False).stdout)
    run_dir.joinpath("codex_model.txt").write_text(os.environ.get("CODEX_MODEL", "codex-cli-local") + "\n")
    run_dir.joinpath("commands.log").write_text("")


def append_command(run_dir: Path, cmd: list[str]) -> None:
    with run_dir.joinpath("commands.log").open("a") as output:
        output.write(f"[{timestamp()}] {' '.join(cmd)}\n")


def write_expert_popularity(run_dir: Path, args: argparse.Namespace, mode: str, steps: int) -> None:
    raw = run_dir / "raw"
    path = raw / "expert_popularity_timeseries.csv"
    with path.open("w", newline="") as output:
        fieldnames = ["step", "time_s", "hot_expert", *[f"expert_{idx}_popularity" for idx in range(args.experts)]]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for step in range(steps):
            weights = weights_for_step(args.experts, step, steps, mode, args.zipf_alpha)
            writer.writerow(
                {
                    "step": step,
                    "time_s": f"{step * args.interval_s:.3f}",
                    "hot_expert": max(range(args.experts), key=lambda idx: weights[idx]),
                    **{f"expert_{idx}_popularity": f"{weights[idx]:.6f}" for idx in range(args.experts)},
                }
            )


def enrich_run(run_dir: Path, args: argparse.Namespace, stage: str, scale: str, replica_level: str, mode: str, steps: int) -> None:
    counts = replica_counts(replica_level, args.experts)
    write_expert_popularity(run_dir, args, mode, steps)
    metadata = {
        "benchmark": "moe-serving",
        "stage": stage,
        "request_types": REQUEST_TYPES,
        "expert_count": args.experts,
        "replica_profile": replica_level,
        **counts,
        "cpu_only_claim_boundary": True,
    }
    run_dir.joinpath("workload_mixer_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    (run_dir / "raw" / "prometheus_resource_envelope.json").write_text(
        json.dumps(
            {
                "evidence_type": "replay",
                "cluster_cpu_utilization": "",
                "cluster_memory_utilization": "",
                "top_node_cpu_utilization": "",
                "note": "No live Prometheus scrape was issued by this replay run.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def run_one(args: argparse.Namespace, stage: str, scale: str, replica_level: str, mode: str, steps: int) -> Path:
    run_id = args.run_id or f"moe-longmix-stage{stage}-{scale}-{replica_level}-{mode}-steps{steps}-{timestamp()}"
    run_dir = REPO_ROOT / "experiments" / "runs" / run_id
    for subdir in ["raw", "processed", "figures", "logs", "env"]:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)
    write_ledger_header(run_dir, args, stage, scale, replica_level, mode, steps)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "experiments" / "continuous_callgraph.py"),
        "--run-dir",
        str(run_dir),
        "--benchmark",
        "moe-serving",
        "--namespace",
        "idyn-moe-serving",
        "--scale",
        scale,
        "--replica-level",
        replica_level,
        "--replica-config",
        replica_config(replica_level, args.experts),
        "--mode",
        mode,
        "--steps",
        str(steps),
        "--interval-s",
        str(args.interval_s),
        "--total-qps",
        str(args.total_qps),
        "--seed",
        str(args.seed),
        "--policies",
        args.policies,
        "--worker-nodes-selected",
        scale.removeprefix("scale"),
        "--actual-app-pods",
        str(replica_counts(replica_level, args.experts)["total_app_pods"]),
        "--ready-app-pods",
        str(replica_counts(replica_level, args.experts)["total_app_pods"]),
        "--non-empty-worker-nodes",
        scale.removeprefix("scale"),
        "--total-pods",
        str(replica_counts(replica_level, args.experts)["total_app_pods"]),
    ]
    append_command(run_dir, cmd)
    result = sh(cmd, check=False)
    (run_dir / "logs" / "continuous_callgraph_stdout.log").write_text(result.stdout)
    (run_dir / "logs" / "continuous_callgraph_stderr.log").write_text(result.stderr)
    if result.returncode != 0:
        raise SystemExit(f"{run_id} failed with exit {result.returncode}: {result.stderr}")
    enrich_run(run_dir, args, stage, scale, replica_level, mode, steps)
    return run_dir


def selected_specs(args: argparse.Namespace) -> list[tuple[str, str, str, str, int]]:
    if args.stage == "single":
        return [(args.stage_label, args.scale, args.replica_profile, args.mode, args.steps)]
    stages = ["A", "B", "C", "D"] if args.stage == "all" else [args.stage]
    return [(stage, *spec) for stage in stages for spec in STAGE_MATRIX[stage]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["single", "A", "B", "C", "D", "all"], default="single")
    parser.add_argument("--stage-label", default="custom")
    parser.add_argument("--scale", default="scale20")
    parser.add_argument("--replica-profile", choices=["replica1", "replica3", "replica5"], default="replica3")
    parser.add_argument("--mode", choices=["step", "linear", "sinusoidal", "markov", "expert_skew_shift", "cache_stress", "payload_heavy"], default="sinusoidal")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--interval-s", type=float, default=0.1)
    parser.add_argument("--total-qps", type=float, default=90.0)
    parser.add_argument("--experts", type=int, default=6)
    parser.add_argument("--zipf-alpha", type=float, default=1.2)
    parser.add_argument("--seed", type=int, default=136)
    parser.add_argument("--policies", default=DEFAULT_POLICIES)
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    if args.stage != "single" and args.run_id:
        raise SystemExit("--run-id is only valid with --stage single")
    manifest = []
    for stage, scale, replica_level, mode, steps in selected_specs(args):
        run_dir = run_one(args, stage, scale, replica_level, mode, steps)
        manifest.append(str(run_dir.relative_to(REPO_ROOT)))
    manifest_path = REPO_ROOT / "experiments" / "runs" / f"moe-longmix-agent136-manifest-{timestamp()}.txt"
    manifest_path.write_text("\n".join(manifest) + "\n")
    print(manifest_path)


if __name__ == "__main__":
    main()
