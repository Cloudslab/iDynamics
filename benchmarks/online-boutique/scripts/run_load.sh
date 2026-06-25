#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-online-boutique}"
port="${IDYN_LOCAL_PORT:-18080}"
duration="${IDYN_DURATION_SECONDS:-45}"
concurrency="${IDYN_CONCURRENCY:-8}"
output="${IDYN_OUTPUT:-/tmp/idyn-online-boutique-load.csv}"

kubectl -n "$namespace" port-forward svc/frontend "$port:80" --address 127.0.0.1 >/tmp/idyn-online-boutique-load-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3

python3 - "$port" "$duration" "$concurrency" "$output" <<'PY'
import csv
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

port, duration, concurrency, output = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
paths = ["/", "/product/0PUK6V6EV0", "/product/2ZYFJ3GM2N", "/cart"]
end = time.time() + duration
rows = []

def request(i):
    idx = 0
    while time.time() < end:
        path = paths[(i + idx) % len(paths)]
        start = time.perf_counter()
        status = 0
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
                response.read()
                status = response.status
        except Exception:
            status = 0
        rows.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": path,
            "status": status,
            "latency_ms": (time.perf_counter() - start) * 1000.0,
        })
        idx += 1

with ThreadPoolExecutor(max_workers=concurrency) as pool:
    list(pool.map(request, range(concurrency)))

with open(output, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["ts", "path", "status", "latency_ms"])
    writer.writeheader()
    writer.writerows(rows)
print(output)
PY
