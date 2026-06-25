#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-social-network}"
out_dir="${IDYN_METRICS_DIR:-/tmp/idyn-social-network-metrics}"
mkdir -p "$out_dir"

kubectl -n "$namespace" get pods -o wide >"$out_dir/pods_wide.txt"
kubectl -n "$namespace" get pods -o json >"$out_dir/pods.json"
kubectl -n "$namespace" get deploy -o wide >"$out_dir/deployments.txt"
kubectl -n "$namespace" get svc -o wide >"$out_dir/services.txt"
kubectl -n "$namespace" get events --sort-by=.lastTimestamp >"$out_dir/events.txt"
kubectl top nodes >"$out_dir/top_nodes.txt" 2>"$out_dir/top_nodes.err" || true
kubectl -n "$namespace" top pods >"$out_dir/top_pods.txt" 2>"$out_dir/top_pods.err" || true

echo "$out_dir"
