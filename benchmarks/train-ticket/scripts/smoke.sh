#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-train-ticket}"
service="${TRAIN_TICKET_ENTRY_SERVICE:-ts-ui-dashboard}"
remote_port="${TRAIN_TICKET_ENTRY_PORT:-80}"
port="${IDYN_LOCAL_PORT:-18082}"

kubectl -n "$namespace" get deploy,svc,pods -o wide
kubectl -n "$namespace" port-forward "svc/$service" "$port:$remote_port" --address 127.0.0.1 >/tmp/idyn-train-ticket-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3
curl -fsS "http://127.0.0.1:$port/" >/dev/null
echo "train-ticket compatibility smoke completed"
