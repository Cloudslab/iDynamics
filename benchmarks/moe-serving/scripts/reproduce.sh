#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
if [[ "${IDYN_LIVE_PHYSICAL:-0}" == "1" ]]; then
  scale="${IDYN_SCALE:-scale10}"
  exec python3 "$repo_root/scripts/experiments/run_physical_moe_k8s.py" \
    --scale "$scale" \
    --replica-profile "${IDYN_REPLICA_PROFILE:-replica1}" \
    --experts "${IDYN_EXPERTS:-6}" \
    --requests "${IDYN_REQUESTS:-120}" \
    --qps "${IDYN_QPS:-10}" \
    --top-k "${IDYN_TOP_K:-2}" \
    --skew-mode "${IDYN_SKEW_MODE:-sinusoidal}" \
    --compute-delay-ms "${IDYN_COMPUTE_DELAY_MS:-5}" \
    --payload-bytes "${IDYN_PAYLOAD_BYTES:-1024}" \
    --seed "${IDYN_SEED:-17}" \
    --image "${MOE_IMAGE:-python:3.11-slim}" \
    ${IDYN_INJECT_SIDECAR:+--inject-sidecar}
fi

cmd=(
  python3 "$repo_root/scripts/experiments/run_moe_longmix_replica.py"
  --stage "${IDYN_STAGE:-single}"
  --scale "${IDYN_SCALE:-scale20}"
  --replica-profile "${IDYN_REPLICA_PROFILE:-replica3}"
  --mode "${IDYN_MODE:-sinusoidal}"
  --steps "${IDYN_STEPS:-200}"
  --interval-s "${IDYN_INTERVAL_S:-0.1}"
  --total-qps "${IDYN_TOTAL_QPS:-90}"
  --experts "${IDYN_EXPERTS:-6}"
  --seed "${IDYN_SEED:-136}"
)
if [[ -n "${IDYN_RUN_ID:-}" ]]; then
  cmd+=(--run-id "$IDYN_RUN_ID")
fi
exec "${cmd[@]}"
