#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-online-boutique}"
port="${IDYN_LOCAL_PORT:-18080}"
checks="${IDYN_SMOKE_REQUESTS:-5}"

kubectl -n "$namespace" get deploy,svc,pods -o wide
kubectl -n "$namespace" port-forward svc/frontend "$port:80" --address 127.0.0.1 >/tmp/idyn-online-boutique-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3

for _ in $(seq 1 "$checks"); do
  curl -fsS "http://127.0.0.1:$port/" >/dev/null
done
echo "online-boutique smoke passed: $checks requests"
