#!/usr/bin/env python3
"""Small dependency-free HTTP load helper for benchmark smoke runs."""

from __future__ import annotations

import argparse
import csv
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run bounded HTTP load and write per-request CSV rows.")
    parser.add_argument("--url", required=True, help="Base URL, for example http://127.0.0.1:18080.")
    parser.add_argument("--paths", default="/", help="Whitespace-separated request paths.")
    parser.add_argument("--duration", type=float, default=30.0, help="Run duration in seconds.")
    parser.add_argument("--concurrency", type=int, default=4, help="Number of worker threads.")
    parser.add_argument("--output", type=Path, required=True, help="CSV output path.")
    return parser.parse_args()


def request_once(url: str) -> dict[str, object]:
    started = time.perf_counter()
    status = 0
    error = ""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            response.read()
            status = response.status
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        error = exc.__class__.__name__
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "status": status,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "error": error,
    }


def worker(base_url: str, paths: list[str], end_time: float, offset: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    idx = offset
    while time.time() < end_time:
        path = paths[idx % len(paths)]
        if not path.startswith("/"):
            path = "/" + path
        rows.append(request_once(base_url.rstrip("/") + path))
        idx += 1
    return rows


def main() -> int:
    args = parse_args()
    paths = [path for path in args.paths.split() if path]
    if not paths:
        raise SystemExit("--paths must include at least one path")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    end_time = time.time() + max(0.1, args.duration)
    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for batch in pool.map(lambda idx: worker(args.url, paths, end_time, idx), range(args.concurrency)):
            rows.extend(batch)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ts", "url", "status", "latency_ms", "error"])
        writer.writeheader()
        writer.writerows(rows)
    latencies = [float(row["latency_ms"]) for row in rows if int(row["status"]) > 0]
    ok = sum(1 for row in rows if 200 <= int(row["status"]) < 400)
    p50 = statistics.median(latencies) if latencies else 0.0
    print(f"{args.output} requests={len(rows)} ok={ok} p50_ms={p50:.3f}")
    return 0 if rows and ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
