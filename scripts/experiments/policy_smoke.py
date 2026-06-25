#!/usr/bin/env python3
"""Ledger-backed smoke experiment for executable Policy 1-4 planners."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from idynamics.ledger.run import init_run_ledger, log_command, utc_timestamp
from idynamics.policies import make_policy
from scripts.policies.run_policy import build_objects, demo_moe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=f"policy-smoke-moe-{utc_timestamp()}")
    parser.add_argument("--experts", type=int, default=4)
    parser.add_argument("--image", default="moe-serving:latest")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ledger = init_run_ledger(
        args.run_id,
        purpose="policy1_policy2_policy3_policy4_moe_smoke",
        root=REPO_ROOT,
        extra_config={
            "workload": "moe-serving-demo",
            "policies": "[policy1, policy2, policy3, policy4]", # Policy 1 and Policy 4 are renamed in the paper.
            "live_kubernetes": "false",
            "network_dynamics": "modeled_matrix_no_tc",
        },
    )
    data = demo_moe()
    (ledger.raw_dir / "policy_smoke_input.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    pods, nodes, graph, network = build_objects(data)

    rows = []
    plans: dict[str, object] = {}
    for policy in ("policy1", "policy2", "policy3", "policy4"):
        planner = make_policy(policy)
        plan = planner.plan_with_details(pods, nodes, graph, network)
        payload = {
            "policy": plan.policy,
            "objective_cost": plan.objective_cost,
            "placement": dict(plan.placement),
            "decisions": [
                {
                    "pod_name": decision.pod_name,
                    "source_node": decision.source_node,
                    "target_node": decision.target_node,
                    "score": decision.score,
                    "reason": decision.reason,
                }
                for decision in plan.decisions
            ],
        }
        plans[policy] = payload
        (ledger.raw_dir / f"{policy}_plan.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        rows.append(
            {
                "policy": policy,
                "policy_name": plan.policy,
                "objective_cost": plan.objective_cost,
                "router_node": plan.placement.get("router", ""),
                "expert0_node": plan.placement.get("expert-0", ""),
                "expert1_node": plan.placement.get("expert-1", ""),
                "placement": json.dumps(dict(plan.placement), sort_keys=True),
            }
        )

        manifest = ledger.raw_dir / f"moe_{policy}_manifest.yaml"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "examples/moe-serving/k8s/render_manifests.py"),
            "--experts",
            str(args.experts),
            "--policy",
            policy,
            "--image",
            args.image,
            "--output",
            str(manifest),
        ]
        log_command(ledger, " ".join(cmd))
        subprocess.run(cmd, check=True)

    (ledger.processed_dir / "policy_smoke_metrics.json").write_text(json.dumps({"rows": rows}, indent=2, sort_keys=True) + "\n")
    csv_lines = ["policy,policy_name,objective_cost,router_node,expert0_node,expert1_node,placement"]
    for row in rows:
        csv_lines.append(
            ",".join(
                [
                    str(row["policy"]),
                    str(row["policy_name"]),
                    f"{float(row['objective_cost']):.9f}",
                    str(row["router_node"]),
                    str(row["expert0_node"]),
                    str(row["expert1_node"]),
                    json.dumps(str(row["placement"])),
                ]
            )
        )
    (ledger.processed_dir / "policy_smoke_metrics.csv").write_text("\n".join(csv_lines) + "\n")

    placements = {policy: row["placement"] for policy, row in zip(("policy1", "policy2", "policy3", "policy4"), rows)}
    p2_distinct = placements["policy2"] != placements["policy1"]
    p3_distinct = placements["policy3"] != placements["policy1"] and placements["policy3"] != placements["policy2"]



if __name__ == "__main__":
    main()
