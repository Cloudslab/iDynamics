#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-online-boutique}"
out_dir="${IDYN_METRICS_DIR:-/tmp/idyn-online-boutique-metrics}"
mkdir -p "$out_dir"

kubectl -n "$namespace" get pods -o wide >"$out_dir/pods_wide.txt"
kubectl -n "$namespace" get pods -o json >"$out_dir/pods.json"
kubectl -n "$namespace" get deploy -o wide >"$out_dir/deployments.txt"
kubectl -n "$namespace" get svc -o wide >"$out_dir/services.txt"
kubectl -n "$namespace" get events --sort-by=.lastTimestamp >"$out_dir/events.txt"
kubectl top nodes >"$out_dir/top_nodes.txt" 2>"$out_dir/top_nodes.err" || true
kubectl -n "$namespace" top pods >"$out_dir/top_pods.txt" 2>"$out_dir/top_pods.err" || true

if kubectl -n istio-system get svc prometheus >/dev/null 2>&1; then
  port="${IDYN_PROM_PORT:-19090}"
  kubectl -n istio-system port-forward svc/prometheus "$port:9090" --address 127.0.0.1 >"$out_dir/prometheus-port-forward.log" 2>&1 &
  pf_pid=$!
  trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
  sleep 3
  query="sum(rate(istio_requests_total{destination_workload_namespace=\"$namespace\"}[2m])) by (source_workload,destination_workload,response_code)"
  curl -fsS --get --data-urlencode "query=$query" "http://127.0.0.1:$port/api/v1/query" >"$out_dir/istio_requests.json" || true
fi

echo "$out_dir"
