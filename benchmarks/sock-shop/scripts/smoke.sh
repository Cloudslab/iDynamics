#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-sock-shop}"
port="${IDYN_LOCAL_PORT:-18083}"

kubectl -n "$namespace" get deploy,svc,pods -o wide
kubectl -n "$namespace" port-forward svc/front-end "$port:80" --address 127.0.0.1 >/tmp/idyn-sock-shop-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3
curl -fsS "http://127.0.0.1:$port/" >/dev/null
echo "sock-shop compatibility smoke completed"
