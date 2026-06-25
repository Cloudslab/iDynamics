#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-dsb-hotel}"
port="${IDYN_LOCAL_PORT:-15000}"

kubectl -n "$namespace" get deploy,svc,pods -o wide
kubectl -n "$namespace" port-forward svc/frontend "$port:5000" --address 127.0.0.1 >/tmp/idyn-hotel-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3
curl -fsS "http://127.0.0.1:$port/" >/dev/null || curl -fsS "http://127.0.0.1:$port/hotels" >/dev/null
echo "deathstar-hotel compatibility smoke completed"
