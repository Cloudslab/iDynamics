#!/usr/bin/env python3
"""Plot DeathStarBench Hotel compatibility latency CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("deathstar_hotel_latency.svg"))
    args = parser.parse_args()
    rows = list(csv.DictReader(args.csv_file.open(encoding="utf-8")))
    latencies = [float(row.get("latency_ms", row.get("latency", 0.0))) for row in rows]
    if not latencies:
        raise SystemExit("no latency rows found")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(5.2, 3.0))
    plt.hist(latencies, bins=30)
    plt.xlabel("Latency (ms)")
    plt.ylabel("Requests")
    plt.title("DeathStar Hotel Latency")
    plt.tight_layout()
    plt.savefig(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
