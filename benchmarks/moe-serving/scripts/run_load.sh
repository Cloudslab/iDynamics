#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
namespace="${IDYN_NAMESPACE:-idyn-moe-serving}"
port="${IDYN_LOCAL_PORT:-18081}"
output="${IDYN_OUTPUT:-/tmp/idyn-moe-load.csv}"

kubectl -n "$namespace" port-forward svc/frontend "$port:8080" --address 127.0.0.1 >/tmp/idyn-moe-load-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3

python3 "$repo_root/examples/moe-serving/workload/generate_load.py" \
  --url "http://127.0.0.1:$port/infer" \
  --experts "${IDYN_EXPERTS:-6}" \
  --requests "${IDYN_REQUESTS:-120}" \
  --qps "${IDYN_QPS:-10}" \
  --top-k "${IDYN_TOP_K:-2}" \
  --skew-mode "${IDYN_SKEW_MODE:-sinusoidal}" \
  --request-type "${IDYN_REQUEST_TYPE:-mixed}" \
  --compute-delay-ms "${IDYN_COMPUTE_DELAY_MS:-5}" \
  --payload-bytes "${IDYN_PAYLOAD_BYTES:-1024}" \
  --seed "${IDYN_SEED:-17}" \
  --output "$output"
