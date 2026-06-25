#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-sock-shop}"
port="${IDYN_LOCAL_PORT:-18083}"
duration="${IDYN_DURATION_SECONDS:-30}"
output="${IDYN_OUTPUT:-/tmp/idyn-sock-shop-load.csv}"

kubectl -n "$namespace" port-forward svc/front-end "$port:80" --address 127.0.0.1 >/tmp/idyn-sock-shop-load-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3

python3 - "$port" "$duration" "$output" <<'PY'
import csv
import sys
import time
import urllib.request
from datetime import datetime, timezone

port, duration, output = sys.argv[1], int(sys.argv[2]), sys.argv[3]
paths = ["/", "/catalogue"]
end = time.time() + duration
rows = []
idx = 0
while time.time() < end:
    path = paths[idx % len(paths)]
    start = time.perf_counter()
    status = 0
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
            response.read()
            status = response.status
    except Exception:
        status = 0
    rows.append({"ts": datetime.now(timezone.utc).isoformat(), "path": path, "status": status, "latency_ms": (time.perf_counter() - start) * 1000.0})
    idx += 1
with open(output, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["ts", "path", "status", "latency_ms"])
    writer.writeheader()
    writer.writerows(rows)
print(output)
PY
