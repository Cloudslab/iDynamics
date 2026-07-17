#!/usr/bin/env python3
"""Generate one reproducibility artifact from its curated data files."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence


POLICY_LABELS = {
    "kubernetes-default": "K8s",
    "cga": "CGA",
    "hda": "HDA",
    "policy2": "Policy2",
    "policy3": "Policy3",
}
MANUSCRIPT_POLICY_SERIES = ("kubernetes-default", "cga", "hda")

MODE_LABELS = {
    "step": "Step",
    "linear": "Linear",
    "sinusoidal": "Sinusoidal",
    "markov": "Markov",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_manifest(artifact_dir: Path) -> dict[str, object]:
    return json.loads((artifact_dir / "manifest.yaml").read_text(encoding="utf-8"))


def as_float(value: object, default: float = math.nan) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return float(text)


def fmt(value: object, digits: int = 3, blank_nan: bool = True) -> str:
    number = as_float(value)
    if math.isnan(number):
        return "" if blank_nan else "nan"
    return f"{number:.{digits}f}"


def fmt_int(value: object) -> str:
    number = as_float(value)
    if math.isnan(number):
        return ""
    return str(int(round(number)))


def markdown_table(rows: Sequence[dict[str, object]], fields: Sequence[str]) -> str:
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines) + "\n"


def latex_table(rows: Sequence[dict[str, object]], fields: Sequence[str], caption: str, label: str) -> str:
    alignment = "l" * len(fields)
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\scriptsize",
        f"\\begin{{tabular}}{{{alignment}}}",
        "\\toprule",
        " & ".join(escape_latex(field) for field in fields) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(escape_latex(str(row.get(field, ""))) for field in fields) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def escape_latex(value: str) -> str:
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def write_table_outputs(
    outdir: Path,
    rows: Sequence[dict[str, object]],
    fields: Sequence[str],
    caption: str,
    label: str,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "table.csv", rows, fields)
    (outdir / "table.md").write_text(markdown_table(rows, fields), encoding="utf-8")
    (outdir / "table.tex").write_text(latex_table(rows, fields, caption, label), encoding="utf-8")


def generate_table_i(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "capability_matrix.csv")
    fields = list(rows[0].keys())
    write_table_outputs(outdir, rows, fields, str(manifest["title"]), str(manifest["label"]))


def generate_table_ii(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "mesh_overhead_summary.csv")
    by_scale = defaultdict(dict)
    for row in rows:
        by_scale[row["scale"]][row["condition"]] = row
    output: list[dict[str, object]] = []
    for scale in sorted(by_scale, key=lambda value: int(value.replace("scale", ""))):
        baseline = by_scale[scale]["no-sidecar"]
        for condition, label in [("no-sidecar", "No-SC"), ("sidecar", "Istio-SC")]:
            row = by_scale[scale][condition]
            cpu = 0.0
            memory = 0.0
            if condition == "sidecar":
                cpu = as_float(row["client_istio-proxy_cpu_cores_mean"], 0.0) + as_float(
                    row["server_istio-proxy_cpu_cores_mean"], 0.0
                )
                memory = as_float(row["client_istio-proxy_memory_mib_mean"], 0.0) + as_float(
                    row["server_istio-proxy_memory_mib_mean"], 0.0
                )
            output.append(
                {
                    "scale": scale.replace("scale", ""),
                    "config": label,
                    "throughput_rps": fmt(row["throughput_rps_mean"], 3),
                    "delta_throughput_rps": "--"
                    if condition == "no-sidecar"
                    else fmt(as_float(row["throughput_rps_mean"]) - as_float(baseline["throughput_rps_mean"]), 3),
                    "p95_ms": fmt(row["p95_ms_mean"], 3),
                    "delta_p95_ms": "--"
                    if condition == "no-sidecar"
                    else fmt(as_float(row["p95_ms_mean"]) - as_float(baseline["p95_ms_mean"]), 3),
                    "p99_ms": fmt(row["p99_ms_mean"], 3),
                    "sidecar_cpu_cores": fmt(cpu, 3),
                    "sidecar_memory_mib": fmt(memory, 1),
                }
            )
    fields = [
        "scale",
        "config",
        "throughput_rps",
        "delta_throughput_rps",
        "p95_ms",
        "delta_p95_ms",
        "p99_ms",
        "sidecar_cpu_cores",
        "sidecar_memory_mib",
    ]
    write_table_outputs(outdir, output, fields, str(manifest["title"]), str(manifest["label"]))


def generate_table_iii(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    output: list[dict[str, object]] = []
    real_specs = [
        ("Online Boutique", artifact_dir / "data" / "gda_live_online_boutique.csv"),
        ("Social Network", artifact_dir / "data" / "gda_live_social_network.csv"),
    ]
    for case, path in real_specs:
        row = read_rows(path)[0]
        output.append(
            {
                "case": case,
                "mode": "sparse",
                "services": fmt_int(row["service_count"]),
                "active_edges": fmt_int(row["active_edges_max"]),
                "queries": fmt_int(row["sparse_query_count"]),
                "query_reduction": f"{fmt(row['query_reduction_ratio_vs_dense'], 1)}x",
                "query_p95_ms": fmt(row["prometheus_query_latency_p95_ms"], 3),
                "build_p95_ms": fmt(row["graph_build_wall_p95_ms"], 3),
                "total_p95_ms": fmt(row["gda_total_wall_p95_ms"], 3),
            }
        )

    synthetic = read_rows(artifact_dir / "data" / "gda_synthetic_summary.csv")
    wanted = {
        (1000, "dense-pairwise"),
        (1000, "sparse-aggregate"),
        (5000, "sparse-aggregate"),
        (10000, "sparse-aggregate"),
        (20000, "sparse-aggregate"),
        (50000, "sparse-aggregate"),
        (50000, "dense-pairwise"),
    }
    for row in synthetic:
        key = (int(as_float(row["service_count"])), row["mode"])
        if key not in wanted:
            continue
        mode = "dense" if row["mode"] == "dense-pairwise" else "sparse"
        output.append(
            {
                "case": f"{human_count(key[0])} services",
                "mode": mode,
                "services": human_count(key[0]),
                "active_edges": human_count(int(as_float(row["active_edges"]))),
                "queries": format_query_count(as_float(row["query_count"]), key[0], mode),
                "query_reduction": f"{format_reduction(as_float(row['query_reduction_ratio_vs_dense']))}x",
                "query_p95_ms": "",
                "build_p95_ms": "" if row["repetitions"] == "0" else fmt(row["graph_build_wall_p95_ms"], 3),
                "total_p95_ms": "",
            }
        )

    fields = [
        "case",
        "mode",
        "services",
        "active_edges",
        "queries",
        "query_reduction",
        "query_p95_ms",
        "build_p95_ms",
        "total_p95_ms",
    ]
    write_table_outputs(outdir, output, fields, str(manifest["title"]), str(manifest["label"]))


def human_count(value: object) -> str:
    number = as_float(value)
    if math.isnan(number):
        return ""
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B".rstrip("0").rstrip(".")
    if number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M".rstrip("0").rstrip(".")
    if number >= 1_000:
        return f"{number / 1_000:.0f}K" if number % 1000 == 0 else f"{number / 1_000:.3f}K".rstrip("0")
    return str(int(number))


def format_query_count(value: float, service_count: int, mode: str) -> str:
    if mode == "dense" and service_count == 50000:
        return "~5B"
    if value == 1_998_000:
        return "1,998K"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B".rstrip("0").rstrip(".")
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M".rstrip("0").rstrip(".")
    if value >= 1_000:
        return f"{value / 1_000:.0f}K" if value % 1000 == 0 else f"{value / 1_000:.3f}K".rstrip("0")
    return str(int(value))


def format_reduction(value: float) -> str:
    if math.isclose(value, 1.0):
        return "1.0"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:.1f}"


def generate_table_iv(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "ndm_accuracy_summary.csv")
    fields = ["metric", "pairs", "mean", "median", "p95", "max"]
    write_table_outputs(outdir, rows, fields, str(manifest["title"]), str(manifest["label"]))


def generate_table_v(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "network_trace_metrics.csv")
    by_key = {(row["provider"], row["metric"]): row for row in rows}
    metrics = [
        ("p50", "p50"),
        ("p95", "p95"),
        ("p99", "p99"),
        ("cv", "coefficient_of_variation"),
        ("peak_to_median", "peak_to_median"),
        ("lag1", "lag1_autocorrelation"),
        ("spatial", "spatial_correlation"),
        ("burst_duration_s", "burst_duration_s"),
    ]
    providers = ["synthetic_distance_random", "burst_correlated", "csv_replay"]
    output = []
    for label, source_metric in metrics:
        out = {"metric": label}
        for provider in providers:
            out[f"latency_{provider}"] = fmt(by_key[(provider, "latency_ms")][source_metric], 3)
            out[f"bandwidth_{provider}"] = fmt(by_key[(provider, "bandwidth_mbps")][source_metric], 3)
        output.append(out)
    fields = ["metric"] + [f"latency_{p}" for p in providers] + [f"bandwidth_{p}" for p in providers]
    write_table_outputs(outdir, output, fields, str(manifest["title"]), str(manifest["label"]))


def generate_table_vi(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "calibration_metrics.csv")
    output = []
    for row in rows:
        output.append(
            {
                "source": row["source"],
                "p50_ms": fmt(row["p50"], 2),
                "p95_ms": fmt(row["p95"], 2),
                "p99_ms": fmt(row["p99"], 2),
                "cv": fmt(row["coefficient_of_variation"], 3),
                "peak_to_median": fmt(row["peak_to_median"], 3),
                "lag1": fmt(row["lag1_autocorrelation"], 3),
                "probe_count": fmt(row["probe_count"], 0),
                "sample_count": fmt(row["sample_count"], 0),
            }
        )
    fields = ["source", "p50_ms", "p95_ms", "p99_ms", "cv", "peak_to_median", "lag1", "probe_count", "sample_count"]
    write_table_outputs(outdir, output, fields, str(manifest["title"]), str(manifest["label"]))


def generate_table_vii(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "request_mix_modes.csv")
    fields = ["mode", "semantics", "representative_run_id"]
    write_table_outputs(outdir, rows, fields, str(manifest["title"]), str(manifest["label"]))


def generate_table_viii(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "continuous_longmix_robustness.csv")
    output = []
    for row in rows:
        output.append(
            {
                "steps": row["steps"],
                "mode": MODE_LABELS.get(row["mode"], row["mode"]),
                "entropy": fmt(row["entropy"], 3),
                "top3_churn": fmt(row["top3_churn"], 3),
                "active_edges": fmt(row["active_edges"], 1),
                "k8s_ms": fmt(row["k8s_ms"], 2),
                "cga_ms": fmt(row["cga_ms"], 2),
                "hda_ms": fmt(row["hda_ms"], 2),
            }
        )
    fields = ["steps", "mode", "entropy", "top3_churn", "active_edges", "k8s_ms", "cga_ms", "hda_ms"]
    write_table_outputs(outdir, output, fields, str(manifest["title"]), str(manifest["label"]))


def generate_figure_07(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "cdf_points.csv")
    write_rows(outdir / "figure_data.csv", rows, ["source", "x_ms", "cdf"])
    series = group_xy(rows, "source", "x_ms", "cdf")
    svg = line_svg(
        series,
        title=str(manifest["title"]),
        x_label="RTT or generated one-way latency (ms)",
        y_label="Empirical CDF",
        width=760,
        height=460,
        x_max=100.0,
        y_min=0.0,
        y_max=1.0,
    )
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "figure.svg").write_text(svg, encoding="utf-8")


def generate_figure_08(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = read_rows(artifact_dir / "data" / "continuous_longmix_500_timeseries.csv")
    write_rows(outdir / "figure_data.csv", rows, list(rows[0].keys()))
    svg = longmix_svg(rows, str(manifest["title"]))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "figure.svg").write_text(svg, encoding="utf-8")


def generate_figure_09(artifact_dir: Path, outdir: Path, manifest: dict[str, object]) -> None:
    rows = [
        row
        for row in read_rows(artifact_dir / "data" / "application_generality_timeseries.csv")
        if row["policy"] in MANUSCRIPT_POLICY_SERIES
    ]
    write_rows(outdir / "figure_data.csv", rows, list(rows[0].keys()))
    svg = application_svg(rows, str(manifest["title"]))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "figure.svg").write_text(svg, encoding="utf-8")


def group_xy(rows: Sequence[dict[str, str]], key_field: str, x_field: str, y_field: str) -> dict[str, list[tuple[float, float]]]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        grouped[row[key_field]].append((as_float(row[x_field]), as_float(row[y_field])))
    return {key: sorted(points) for key, points in grouped.items()}


def line_svg(
    series: dict[str, list[tuple[float, float]]],
    *,
    title: str,
    x_label: str,
    y_label: str,
    width: int,
    height: int,
    x_max: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
) -> str:
    margin = {"left": 72, "right": 34, "top": 58, "bottom": 64}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    all_x = [point[0] for points in series.values() for point in points]
    all_y = [point[1] for points in series.values() for point in points]
    xmin = 0.0
    xmax = x_max if x_max is not None else max(all_x)
    ymin = min(all_y) if y_min is None else y_min
    ymax = max(all_y) if y_max is None else y_max
    if math.isclose(ymin, ymax):
        ymax = ymin + 1.0

    def sx(x: float) -> float:
        return margin["left"] + max(0.0, min(x, xmax) - xmin) / (xmax - xmin) * plot_w

    def sy(y: float) -> float:
        return margin["top"] + (ymax - y) / (ymax - ymin) * plot_h

    colors = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c"]
    parts = svg_header(width, height, title)
    parts.append(axis_block(width, height, margin, plot_w, plot_h, x_label, y_label))
    for idx, (name, points) in enumerate(series.items()):
        path = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
        parts.append(f'<polyline fill="none" stroke="{colors[idx % len(colors)]}" stroke-width="2" points="{path}"/>')
        lx = margin["left"] + 16
        ly = margin["top"] + 18 + idx * 20
        parts.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 22}" y2="{ly}" stroke="{colors[idx % len(colors)]}" stroke-width="2"/>')
        parts.append(f'<text x="{lx + 30}" y="{ly + 4}" font-size="12">{html.escape(name)}</text>')
    add_ticks(parts, margin, plot_w, plot_h, xmin, xmax, ymin, ymax)
    parts.append("</g></svg>\n")
    return "\n".join(parts)


def svg_header(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<rect width=\"100%\" height=\"100%\" fill=\"#ffffff\"/>",
        f'<text x="{width / 2:.1f}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="17" font-weight="700">{html.escape(title)}</text>',
        '<g font-family="Arial, sans-serif" fill="#111827">',
    ]


def axis_block(
    width: int,
    height: int,
    margin: dict[str, int],
    plot_w: int,
    plot_h: int,
    x_label: str,
    y_label: str,
) -> str:
    x0 = margin["left"]
    y0 = margin["top"]
    y_axis_bottom = y0 + plot_h
    return "\n".join(
        [
            f'<rect x="{x0}" y="{y0}" width="{plot_w}" height="{plot_h}" fill="#f8fafc" stroke="#cbd5e1"/>',
            f'<line x1="{x0}" y1="{y_axis_bottom}" x2="{x0 + plot_w}" y2="{y_axis_bottom}" stroke="#111827"/>',
            f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y_axis_bottom}" stroke="#111827"/>',
            f'<text x="{width / 2:.1f}" y="{height - 18}" text-anchor="middle" font-size="13">{html.escape(x_label)}</text>',
            f'<text x="18" y="{height / 2:.1f}" transform="rotate(-90 18 {height / 2:.1f})" text-anchor="middle" font-size="13">{html.escape(y_label)}</text>',
        ]
    )


def add_ticks(
    parts: list[str],
    margin: dict[str, int],
    plot_w: int,
    plot_h: int,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
) -> None:
    x0 = margin["left"]
    y0 = margin["top"]
    bottom = y0 + plot_h
    for idx in range(6):
        value = xmin + (xmax - xmin) * idx / 5
        x = x0 + plot_w * idx / 5
        parts.append(f'<line x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom + 5}" stroke="#111827"/>')
        parts.append(f'<text x="{x:.1f}" y="{bottom + 20}" text-anchor="middle" font-size="11">{value:.0f}</text>')
    for idx in range(5):
        value = ymin + (ymax - ymin) * idx / 4
        y = bottom - plot_h * idx / 4
        parts.append(f'<line x1="{x0 - 5}" y1="{y:.1f}" x2="{x0}" y2="{y:.1f}" stroke="#111827"/>')
        parts.append(f'<text x="{x0 - 9}" y="{y + 4:.1f}" text-anchor="end" font-size="11">{value:.2f}</text>')


def longmix_svg(rows: Sequence[dict[str, str]], title: str) -> str:
    width, height = 980, 720
    modes = ["step", "linear", "sinusoidal", "markov"]
    colors = {"kubernetes-default": "#64748b", "cga": "#2563eb", "hda": "#dc2626"}
    parts = svg_header(width, height, title)
    panel_w = 420
    panel_h = 130
    left_x = 74
    right_x = 530
    top = 62
    row_gap = 154
    by_mode = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)
    for idx, mode in enumerate(modes):
        y = top + idx * row_gap
        mode_rows = by_mode[mode]
        draw_panel(parts, left_x, y, panel_w, panel_h, mode_rows, "step", ["p_read_home", "p_compose_post", "p_read_user"], [("#2563eb", "read_home"), ("#059669", "compose"), ("#ea580c", "read_user")], y_label="mix")
        draw_panel(parts, right_x, y, panel_w, panel_h, mode_rows, "step", ["latency_kubernetes-default_ms", "latency_cga_ms", "latency_hda_ms"], [(colors["kubernetes-default"], "K8s"), (colors["cga"], "CGA"), (colors["hda"], "HDA")], y_label="ms")
        parts.append(f'<text x="30" y="{y + 72}" font-size="14" font-weight="700" transform="rotate(-90 30 {y + 72})">{MODE_LABELS[mode]}</text>')
    parts.append("</g></svg>\n")
    return "\n".join(parts)


def application_svg(rows: Sequence[dict[str, str]], title: str) -> str:
    width, height = 980, 520
    parts = svg_header(width, height, title)
    benchmarks = ["online-boutique", "moe-serving"]
    top = 70
    panel_w = 410
    panel_h = 320
    for idx, benchmark in enumerate(benchmarks):
        x = 74 + idx * 456
        panel_rows = [row for row in rows if row["benchmark"] == benchmark]
        collapsed = collapse_policy_rows(panel_rows)
        fields: set[str] = set()
        for row in collapsed:
            fields.update(key for key in row if key.startswith("latency_"))
        legends = []
        for color, policy in [("#64748b", "kubernetes-default"), ("#2563eb", "cga"), ("#dc2626", "hda")]:
            field = f"latency_{POLICY_LABELS[policy].lower()}_ms"
            if field in fields:
                legends.append((color, POLICY_LABELS[policy]))
        draw_panel(parts, x, top, panel_w, panel_h, collapsed, "step", [f"latency_{label.lower()}_ms" for _, label in legends], legends, y_label="ms")
        parts.append(f'<text x="{x + panel_w / 2:.1f}" y="{top + panel_h + 38}" text-anchor="middle" font-size="14" font-weight="700">{html.escape(benchmark)}</text>')
    parts.append("</g></svg>\n")
    return "\n".join(parts)


def collapse_policy_rows(rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    collapsed: dict[str, dict[str, str]] = {}
    for row in rows:
        step = row["step"]
        out = collapsed.setdefault(step, {"step": step})
        label = POLICY_LABELS.get(row["policy"], row["policy"]).lower()
        out[f"latency_{label}_ms"] = row["latency_ms"]
    return [collapsed[key] for key in sorted(collapsed, key=lambda item: int(item))]


def draw_panel(
    parts: list[str],
    x: int,
    y: int,
    w: int,
    h: int,
    rows: Sequence[dict[str, str]],
    x_field: str,
    y_fields: Sequence[str],
    legends: Sequence[tuple[str, str]],
    *,
    y_label: str,
) -> None:
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f8fafc" stroke="#cbd5e1"/>')
    if not rows:
        return
    xs = [as_float(row[x_field]) for row in rows]
    ys = [as_float(row[field]) for row in rows for field in y_fields if row.get(field, "") != ""]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if math.isclose(ymin, ymax):
        ymax += 1.0
    ypad = (ymax - ymin) * 0.08
    ymin -= ypad
    ymax += ypad

    def sx(value: float) -> float:
        return x + 12 + (value - xmin) / (xmax - xmin) * (w - 24)

    def sy(value: float) -> float:
        return y + 12 + (ymax - value) / (ymax - ymin) * (h - 24)

    for field, (color, _) in zip(y_fields, legends):
        points = [(as_float(row[x_field]), as_float(row[field])) for row in rows if row.get(field, "") != ""]
        if len(points) < 2:
            continue
        point_text = " ".join(f"{sx(px):.2f},{sy(py):.2f}" for px, py in points)
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.6" points="{point_text}"/>')
    parts.append(f'<text x="{x + 4}" y="{y + 14}" font-size="10">{html.escape(y_label)}</text>')
    lx = x + 12
    ly = y + h - 8
    for idx, (color, label) in enumerate(legends):
        parts.append(f'<line x1="{lx + idx * 72}" y1="{ly}" x2="{lx + 18 + idx * 72}" y2="{ly}" stroke="{color}" stroke-width="1.8"/>')
        parts.append(f'<text x="{lx + 22 + idx * 72}" y="{ly + 4}" font-size="10">{html.escape(label)}</text>')


GENERATORS = {
    "table-i": generate_table_i,
    "table-ii": generate_table_ii,
    "table-iii": generate_table_iii,
    "table-iv": generate_table_iv,
    "table-v": generate_table_v,
    "table-vi": generate_table_vi,
    "table-vii": generate_table_vii,
    "table-viii": generate_table_viii,
    "figure-07": generate_figure_07,
    "figure-08": generate_figure_08,
    "figure-09": generate_figure_09,
}


def generate(artifact_dir: Path, output_dir: Path | None = None) -> Path:
    artifact_dir = artifact_dir.resolve()
    manifest = read_manifest(artifact_dir)
    item_id = str(manifest["item_id"])
    if item_id not in GENERATORS:
        raise SystemExit(f"unsupported artifact item_id: {item_id}")
    outdir = (output_dir or artifact_dir / "generated").resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    GENERATORS[item_id](artifact_dir, outdir, manifest)
    return outdir


def cli(default_artifact_dir: Path | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", nargs="?", type=Path, default=default_artifact_dir)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.artifact_dir is None:
        parser.error("artifact_dir is required")
    outdir = generate(args.artifact_dir, args.output_dir)
    print(outdir)


if __name__ == "__main__":
    cli()
