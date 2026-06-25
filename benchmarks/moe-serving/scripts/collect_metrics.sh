#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-moe-serving}"
out_dir="${IDYN_METRICS_DIR:-/tmp/idyn-moe-serving-metrics}"
port="${IDYN_LOCAL_PORT:-18081}"
mkdir -p "$out_dir"

kubectl -n "$namespace" get pods -o wide >"$out_dir/pods_wide.txt"
kubectl -n "$namespace" get pods -o json >"$out_dir/pods.json"
kubectl -n "$namespace" get deploy -o wide >"$out_dir/deployments.txt"
kubectl -n "$namespace" get svc -o wide >"$out_dir/services.txt"
kubectl -n "$namespace" get events --sort-by=.lastTimestamp >"$out_dir/events.txt"
kubectl top nodes >"$out_dir/top_nodes.txt" 2>"$out_dir/top_nodes.err" || true
kubectl -n "$namespace" top pods >"$out_dir/top_pods.txt" 2>"$out_dir/top_pods.err" || true
cat >"$out_dir/prometheus_resource_envelope.json" <<JSON
{
  "evidence_type": "live_collection",
  "top_nodes_file": "top_nodes.txt",
  "top_pods_file": "top_pods.txt",
  "frontend_metrics_file": "frontend_metrics.prom",
  "note": "Metrics API output is archived verbatim; parse before using in reported results."
}
JSON

kubectl -n "$namespace" port-forward svc/frontend "$port:8080" --address 127.0.0.1 >"$out_dir/frontend-port-forward.log" 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3
curl -fsS "http://127.0.0.1:$port/metrics" >"$out_dir/frontend_metrics.prom" || true

echo "$out_dir"
