#!/usr/bin/env python3
"""Plot Online Boutique load summaries from a run ledger."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source = args.run_dir / "processed" / "load_summary.csv"
    output = args.output or args.run_dir / "figures" / "online_boutique_latency.svg"
    rows = list(csv.DictReader(source.open(encoding="utf-8")))
    if not rows:
        raise SystemExit(f"no rows in {source}")

    import matplotlib.pyplot as plt

    repeats = [int(row["repeat"]) for row in rows]
    p50 = [float(row["p50_ms"]) for row in rows]
    p95 = [float(row["p95_ms"]) for row in rows]
    p99 = [float(row["p99_ms"]) for row in rows]

    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(5.5, 3.2))
    plt.plot(repeats, p50, marker="o", label="p50")
    plt.plot(repeats, p95, marker="s", label="p95")
    plt.plot(repeats, p99, marker="^", label="p99")
    plt.xlabel("Repeat")
    plt.ylabel("Latency (ms)")
    plt.title("Online Boutique Latency")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
