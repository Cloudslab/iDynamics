#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-social-network}"
port="${IDYN_LOCAL_PORT:-18083}"
duration="${IDYN_DURATION_SECONDS:-45}"
concurrency="${IDYN_CONCURRENCY:-8}"
output="${IDYN_OUTPUT:-/tmp/idyn-social-network-load.csv}"

kubectl -n "$namespace" port-forward svc/nginx-thrift "$port:8080" --address 127.0.0.1 >/tmp/idyn-social-network-load-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3

python3 - "$port" "$duration" "$concurrency" "$output" <<'PY'
import csv
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

port, duration, concurrency, output = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
end = time.time() + duration
rows = []

def request(idx):
    while time.time() < end:
        if idx % 10 == 0:
            body = urllib.parse.urlencode({
                "username": "username_1",
                "user_id": "1",
                "text": "idynamics social-network benchmark",
                "media_ids": "[]",
                "media_types": "[]",
                "post_type": "0",
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/wrk2-api/post/compose", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        elif idx % 10 < 7:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/wrk2-api/home-timeline/read?user_id=1&start=0&stop=10")
        else:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/wrk2-api/user-timeline/read?user_id=1&start=0&stop=10")
        started = time.perf_counter()
        status = 0
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                response.read()
                status = response.status
        except Exception:
            status = 0
        rows.append({"ts": datetime.now(timezone.utc).isoformat(), "status": status, "latency_ms": (time.perf_counter() - started) * 1000.0})

with ThreadPoolExecutor(max_workers=concurrency) as pool:
    list(pool.map(request, range(concurrency)))

with open(output, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["ts", "status", "latency_ms"])
    writer.writeheader()
    writer.writerows(rows)
print(output)
PY
