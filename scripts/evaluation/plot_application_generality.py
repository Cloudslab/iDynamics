#!/usr/bin/env python3
"""Generate Sixth-pass application-generality figures from run-ledger CSV inputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


RUNS_ROOT = Path("experiments/runs")


DEFAULT_OB_RUN = "online-boutique-longmix-stageB-scale45-replica5-sinusoidal-steps500-20260612T140712Z"
DEFAULT_MOE_RUN = "moe-longmix-stageB-scale45-replica5-markov-steps500-20260612T141948Z"
DEFAULT_OB_PREFIX = "online-boutique-longmix-stageB-scale45-replica5-sinusoidal-steps500-"
DEFAULT_MOE_PREFIX = "moe-longmix-stageB-scale45-replica5-markov-steps500-"


REQUEST_EXCLUDE = {"p_index"}

POLICY_PRIORITY = (
    "kubernetes-default",
    "cga",
    "hda",
    "policy-2",
    "policy2",
    "policy-3",
    "policy3",
)

POLICY_LABELS = {
    "kubernetes-default": "K8s",
    "cga": "CGA",
    "hda": "HDA",
    "policy-2": "Policy 2",
    "policy2": "Policy 2",
    "policy-3": "Policy 3",
    "policy3": "Policy 3",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", default="experiments/runs")
    parser.add_argument("--output-dir", default="revisionFigures/sixth_pass")
    parser.add_argument(
        "--paper-figure-dir",
        default="paperSourceFiles/iDynamics_Revision1_fourthPass/Figure/revised",
    )
    parser.add_argument("--ob-run-id", help="Online Boutique long-mix run id")
    parser.add_argument("--moe-run-id", help="MoE long-mix run id")
    parser.add_argument("--dpi", type=int, default=220)
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"missing or empty CSV: {path}")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV rows: {path}")
    return rows


def to_float(value: str) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def find_default_run(runs_root: Path, hint: str, prefix: str) -> Path:
    if hint:
        path = runs_root / hint
        if path.exists():
            required = [
                path / "raw" / "request_mix_timeseries.csv",
                path / "raw" / "application_policy_timeseries.csv",
                path / "processed" / "application_metrics_summary.csv",
                path / "processed" / "gda_runtime_summary.csv",
            ]
            if all(item.exists() and item.stat().st_size > 0 for item in required):
                return path
    matches = sorted(runs_root.glob(prefix))
    for candidate in matches:
        required = [
            candidate / "raw" / "request_mix_timeseries.csv",
            candidate / "raw" / "application_policy_timeseries.csv",
            candidate / "processed" / "application_metrics_summary.csv",
            candidate / "processed" / "gda_runtime_summary.csv",
        ]
        if all(item.exists() and item.stat().st_size > 0 for item in required):
            return candidate
    raise FileNotFoundError(f"no matching complete run for {prefix}")


def get_request_columns(mix_rows: list[dict[str, str]]) -> list[str]:
    if not mix_rows:
        return []
    candidates = [col for col in mix_rows[0].keys() if col.startswith("p_") and col not in REQUEST_EXCLUDE]
    # keep all request-probability columns (sorted by mean magnitude for readability)
    means: list[tuple[str, float]] = []
    for col in candidates:
        values = [to_float(row.get(col, "")) for row in mix_rows]
        values = [v for v in values if v is not None]
        if not values:
            continue
        means.append((col, sum(values) / len(values)))
    means.sort(key=lambda item: (-item[1], item[0]))
    keep = [name for name, _ in means]
    return keep


def get_steps(rows: list[dict[str, str]]) -> list[float]:
    steps: list[float] = []
    for row in rows:
        value = to_float(row.get("step", ""))
        if value is not None:
            steps.append(value)
    if not steps:
        return []
    min_step = min(steps)
    return [step - min_step for step in steps]


def policy_timeseries_rows(policy_rows: list[dict[str, str]]) -> dict[str, list[dict[str, float]]]:
    by_policy: dict[str, list[dict[str, float]]] = {}
    for row in policy_rows:
        policy = (row.get("policy") or "").strip()
        if not policy:
            continue
        step = to_float(row.get("step", ""))
        if step is None:
            continue
        entry: dict[str, float] = {"step": step}
        for field in (
            "weighted_edge_distance",
            "active_edge_count",
            "gda_total_time_ms",
            "latency_ms",
            "request_mix_entropy",
        ):
            value = to_float(row.get(field, ""))
            if value is not None:
                entry[field] = value
        by_policy.setdefault(policy, []).append(entry)
    for entries in by_policy.values():
        entries.sort(key=lambda item: item["step"])
    return by_policy


def plot_request_mix(ax: Any, mix_rows: list[dict[str, str]]) -> list[str]:
    request_cols = get_request_columns(mix_rows)
    steps = get_steps(mix_rows)
    if not request_cols or not steps:
        ax.text(0.5, 0.5, "missing request mix series", ha="center", va="center")
        return request_cols
    limit = min(len(request_cols), 8)
    for idx, column in enumerate(request_cols[:limit]):
        ys = [to_float(row.get(column, "")) for row in mix_rows]
        xs = [s for s, y in zip(steps, ys) if y is not None]
        ys = [y for y in ys if y is not None]
        if not ys:
            continue
        ax.plot(xs, ys, label=column[2:].replace("_", " "), linewidth=1.1)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Request mix")
    ax.set_title("Request mix proportions")
    ax.grid(True, alpha=0.25, linewidth=0.6)
    ax.legend(loc="upper right", fontsize=7, ncol=2, frameon=False)
    return request_cols


def plot_graph_metrics(ax: Any, mix_rows: list[dict[str, str]]) -> None:
    steps = get_steps(mix_rows)
    if not steps:
        ax.text(0.5, 0.5, "missing graph trace", ha="center", va="center")
        return
    active = [to_float(row.get("active_edge_count", "")) for row in mix_rows]
    dist = [to_float(row.get("weighted_edge_distance", "")) for row in mix_rows]
    valid = [(x, y) for x, y in zip(steps, active) if y is not None]
    if valid:
        xs, ys = zip(*valid)
        ax.plot(xs, ys, label="active edges", linewidth=1.2, color="#2f6f9f")
        ax.set_ylabel("Active edges", color="#2f6f9f")
        ax.tick_params(axis="y", labelcolor="#2f6f9f")
    ax2 = ax.twinx()
    valid = [(x, y) for x, y in zip(steps, dist) if y is not None]
    if valid:
        xs, ys = zip(*valid)
        ax2.plot(xs, ys, label="weighted edge dist", linewidth=1.2, color="#b4574d")
        ax2.set_ylabel("Weighted edge distance", color="#b4574d")
        ax2.tick_params(axis="y", labelcolor="#b4574d")
    ax.set_xlabel("Step")
    ax.set_title("Graph evolution")
    ax.grid(True, alpha=0.25, linewidth=0.6)


def plot_policy_panel(ax: Any, by_policy: dict[str, list[dict[str, float]]], field: str, title: str, default_label: str) -> None:
    plotted = False
    for policy in POLICY_PRIORITY:
        entries = by_policy.get(policy, [])
        if not entries:
            continue
        xs = [row["step"] for row in entries if field in row]
        ys = [row[field] for row in entries if field in row]
        if not ys:
            continue
        ax.plot(xs, ys, label=POLICY_LABELS.get(policy, policy), linewidth=1.1)
        plotted = True
    if not plotted:
        ax.text(0.5, 0.5, f"missing {default_label}", ha="center", va="center")
    else:
        ax.legend(loc="upper right", fontsize=7, frameon=False)
    ax.set_title(title)
    ax.set_xlabel("Step")
    ax.grid(True, alpha=0.25, linewidth=0.6)


def write_manifest(manifest_path: Path, payload: dict[str, Any]) -> None:
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_mode(run_dir: Path) -> str:
    return run_dir.name.split("-steps")[0].rsplit("-", 1)[-1]


def build_figure(
    run_dir: Path,
    output_dir: Path,
    paper_dir: Path,
    figure_slug: str,
    evidence_boundary: str,
    dpi: int,
    command: str,
    mode_label: str,
) -> tuple[Path, Path]:
    mix_rows = read_csv_rows(run_dir / "raw" / "request_mix_timeseries.csv")
    policy_rows = read_csv_rows(run_dir / "raw" / "application_policy_timeseries.csv")
    by_policy = policy_timeseries_rows(policy_rows)
    policy_count = sum(1 for _ in policy_rows if _.get("policy"))
    summary_rows = read_csv_rows(run_dir / "processed" / "application_metrics_summary.csv")

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0))
    request_cols = plot_request_mix(axes[0][0], mix_rows)
    plot_graph_metrics(axes[0][1], mix_rows)
    plot_policy_panel(
        axes[1][0],
        by_policy,
        "gda_total_time_ms",
        "Replay GDA total time (ms)",
        "GDA timing traces",
    )
    plot_policy_panel(
        axes[1][1],
        by_policy,
        "latency_ms",
        "Replay latency trace (ms)",
        "latency traces",
    )

    fig.suptitle(
        f"{figure_slug.replace('_', ' ').title()} dynamics ({mode_label}) — long-mix replay evidence",
        fontsize=11,
    )
    fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.94))
    footnote = (
        f"Run: {run_dir.name}; policies in file: {policy_count}; "
        f"request columns: {', '.join(request_cols[:8]) or 'none'}"
    )
    fig.text(0.02, 0.01, footnote, fontsize=7)

    output_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / f"application_generality_{figure_slug}_timeseries.png"
    pdf_path = output_dir / f"application_generality_{figure_slug}_timeseries.pdf"
    fig.savefig(png_path, dpi=dpi)
    fig.savefig(pdf_path)
    fig.savefig(paper_dir / png_path.name, dpi=dpi)
    fig.savefig(paper_dir / pdf_path.name)
    plt.close(fig)

    data_sources = [
        str((run_dir / "raw" / "request_mix_timeseries.csv")),
        str((run_dir / "raw" / "application_policy_timeseries.csv")),
        str((run_dir / "processed" / "application_metrics_summary.csv")),
        str((run_dir / "processed" / "gda_runtime_summary.csv")),
    ]
    evidence_rows = [row for row in summary_rows if row.get("policy") == "cga"]
    if not evidence_rows:
        evidence_rows = summary_rows[:1]
    occupancy = evidence_rows[0].get("pod_node_occupancy_ratio", "n/a")
    write_manifest(
        output_dir / f"application_generality_{figure_slug}_timeseries_manifest.json",
        {
            "artifact_png": str(png_path),
            "artifact_pdf": str(pdf_path),
            "paper_png": str(paper_dir / png_path.name),
            "paper_pdf": str(paper_dir / pdf_path.name),
            "paper_section": "VIII-F",
            "figure_label": f"fig:application_generality_{figure_slug}_timeseries",
            "claim_boundary": evidence_boundary,
            "run_id": run_dir.name,
            "evidence_type": evidence_rows[0].get("evidence_type", "replay"),
            "occupancy_ratio": occupancy,
            "scale": evidence_rows[0].get("scale"),
            "replica_level": evidence_rows[0].get("replica_level"),
            "mode": evidence_rows[0].get("workload_mode"),
            "command": command,
            "inputs": data_sources,
        },
    )
    return png_path, pdf_path


def main() -> int:
    args = parse_args()
    runs_root = Path(args.runs_root)

    ob_run = find_default_run(
        runs_root,
        args.ob_run_id or "",
        f"{DEFAULT_OB_PREFIX}*",
    )
    moe_run = find_default_run(
        runs_root,
        args.moe_run_id or "",
        f"{DEFAULT_MOE_PREFIX}*",
    )

    output_dir = Path(args.output_dir)
    paper_dir = Path(args.paper_figure_dir)

    ob_cmd = (
        f"python3 scripts/evaluation/plot_application_generality.py "
        f"--runs-root experiments/runs --output-dir {output_dir} --paper-figure-dir {paper_dir} "
        f"--ob-run-id {ob_run.name}"
    )
    moe_cmd = (
        f"python3 scripts/evaluation/plot_application_generality.py "
        f"--runs-root experiments/runs --output-dir {output_dir} --paper-figure-dir {paper_dir} "
        f"--moe-run-id {moe_run.name}"
    )

    ob_paths = build_figure(
        ob_run,
        output_dir,
        paper_dir,
        "online_boutique",
        "Long-mix request-mix/call-graph replay evidence; not a live stress benchmark claim.",
        args.dpi,
        ob_cmd,
        extract_mode(ob_run),
    )
    moe_paths = build_figure(
        moe_run,
        output_dir,
        paper_dir,
        "moe",
        "MoE long-mix replay evidence with replay-only policy traces; no GPU-only routing claim.",
        args.dpi,
        moe_cmd,
        extract_mode(moe_run),
    )
    print("\n".join(str(path) for path in [*ob_paths, *moe_paths]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
