#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-sock-shop}"
out_dir="${IDYN_METRICS_DIR:-/tmp/idyn-sock-shop-metrics}"
mkdir -p "$out_dir"
kubectl -n "$namespace" get pods -o wide >"$out_dir/pods_wide.txt"
kubectl -n "$namespace" get pods -o json >"$out_dir/pods.json"
kubectl -n "$namespace" get deploy -o wide >"$out_dir/deployments.txt"
kubectl -n "$namespace" get svc -o wide >"$out_dir/services.txt"
kubectl -n "$namespace" get events --sort-by=.lastTimestamp >"$out_dir/events.txt"
echo "$out_dir"
