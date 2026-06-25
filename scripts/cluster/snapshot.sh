#!/usr/bin/env bash
set -euo pipefail

kubectl_bin="${KUBECTL:-kubectl}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output_dir="${1:-cluster_snapshot_${timestamp}}"

if ! command -v "$kubectl_bin" >/dev/null 2>&1; then
  echo "kubectl command not found: $kubectl_bin" >&2
  exit 127
fi

mkdir -p "$output_dir"

"$kubectl_bin" version --client=true >"$output_dir/kubectl_version.txt"

if ! "$kubectl_bin" cluster-info >"$output_dir/cluster_info.txt" 2>"$output_dir/cluster_info.err"; then
  echo "kubectl cannot reach a cluster; wrote client snapshot to $output_dir" >&2
  exit 0
fi

"$kubectl_bin" get nodes -o wide >"$output_dir/nodes_wide.txt"
"$kubectl_bin" get pods --all-namespaces -o wide >"$output_dir/pods_all_namespaces_wide.txt"
"$kubectl_bin" get svc --all-namespaces -o wide >"$output_dir/services_all_namespaces_wide.txt"
"$kubectl_bin" get deploy --all-namespaces -o wide >"$output_dir/deployments_all_namespaces_wide.txt"
"$kubectl_bin" get ds --all-namespaces -o wide >"$output_dir/daemonsets_all_namespaces_wide.txt"
"$kubectl_bin" get events --all-namespaces --sort-by=.lastTimestamp >"$output_dir/events_all_namespaces.txt" || true

echo "cluster snapshot written to $output_dir"
