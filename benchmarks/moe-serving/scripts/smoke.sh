#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-moe-serving}"
port="${IDYN_LOCAL_PORT:-18081}"

kubectl -n "$namespace" get deploy,svc,pods -o wide
kubectl -n "$namespace" port-forward svc/frontend "$port:8080" --address 127.0.0.1 >/tmp/idyn-moe-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3

curl -fsS -X POST "http://127.0.0.1:$port/infer" \
  -H 'content-type: application/json' \
  -d '{"request_id":"smoke","experts":[0,1],"payload_bytes":128}' >/dev/null
echo "moe-serving smoke passed"
