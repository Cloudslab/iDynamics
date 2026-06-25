#!/usr/bin/env python3
"""Plot TrainTicket compatibility load CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("train_ticket_latency.svg"))
    args = parser.parse_args()
    rows = list(csv.DictReader(args.csv_file.open(encoding="utf-8")))
    latencies = [float(row["latency_ms"]) for row in rows if row.get("status") and int(row["status"]) < 500]
    if not latencies:
        raise SystemExit("no successful latency rows found")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(5.2, 3.0))
    plt.plot(range(1, len(latencies) + 1), latencies)
    plt.xlabel("Request")
    plt.ylabel("Latency (ms)")
    plt.title("TrainTicket Smoke Latency")
    plt.tight_layout()
    plt.savefig(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
