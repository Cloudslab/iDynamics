#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
namespace="${IDYN_NAMESPACE:-idyn-moe-serving}"
scale="${IDYN_SCALE:-scale10}"
policy="${IDYN_POLICY:-default}"
experts="${IDYN_EXPERTS:-6}"
image="${MOE_IMAGE:-moe-serving:latest}"
manifest="${IDYN_MANIFEST:-/tmp/idyn-moe-serving-${namespace}.yaml}"
node_pool_label="${IDYN_NODE_POOL_LABEL-idynamics.dev/$scale=true}"

render_cmd=(
  python3 "$repo_root/examples/moe-serving/k8s/render_manifests.py"
  --namespace "$namespace"
  --experts "$experts"
  --policy "$policy"
  --hot-experts "${IDYN_HOT_EXPERTS:-0,1}"
  --image "$image"
  --compute-delay-ms "${IDYN_COMPUTE_DELAY_MS:-5}"
  --payload-bytes "${IDYN_PAYLOAD_BYTES:-256}"
  --cache-hit-ratio "${IDYN_CACHE_HIT_RATIO:-0.0}"
  --output "$manifest"
)
if [[ -n "$node_pool_label" ]]; then
  render_cmd+=(--node-pool-label "$node_pool_label")
fi

"${render_cmd[@]}"

kubectl apply -f "$manifest"
kubectl -n "$namespace" rollout status deployment --all --timeout="${IDYN_ROLLOUT_TIMEOUT:-240s}"
printf '%s\n' "$manifest"
