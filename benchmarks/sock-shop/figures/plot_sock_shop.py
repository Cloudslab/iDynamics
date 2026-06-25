#!/usr/bin/env python3
"""Plot Sock Shop compatibility load CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("sock_shop_latency.svg"))
    args = parser.parse_args()
    rows = list(csv.DictReader(args.csv_file.open(encoding="utf-8")))
    latencies = [float(row["latency_ms"]) for row in rows if row.get("status") and int(row["status"]) < 500]
    if not latencies:
        raise SystemExit("no successful latency rows found")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(5.2, 3.0))
    plt.hist(latencies, bins=25)
    plt.xlabel("Latency (ms)")
    plt.ylabel("Requests")
    plt.title("Sock Shop Smoke Latency")
    plt.tight_layout()
    plt.savefig(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
