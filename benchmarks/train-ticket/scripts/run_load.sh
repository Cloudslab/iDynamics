#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-train-ticket}"
service="${TRAIN_TICKET_ENTRY_SERVICE:-ts-ui-dashboard}"
remote_port="${TRAIN_TICKET_ENTRY_PORT:-80}"
port="${IDYN_LOCAL_PORT:-18082}"
duration="${IDYN_DURATION_SECONDS:-30}"
output="${IDYN_OUTPUT:-/tmp/idyn-train-ticket-load.csv}"

kubectl -n "$namespace" port-forward "svc/$service" "$port:$remote_port" --address 127.0.0.1 >/tmp/idyn-train-ticket-load-port-forward.log 2>&1 &
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
end = time.time() + duration
rows = []
while time.time() < end:
    start = time.perf_counter()
    status = 0
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            response.read()
            status = response.status
    except Exception:
        status = 0
    rows.append({"ts": datetime.now(timezone.utc).isoformat(), "status": status, "latency_ms": (time.perf_counter() - start) * 1000.0})
with open(output, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["ts", "status", "latency_ms"])
    writer.writeheader()
    writer.writerows(rows)
print(output)
PY
