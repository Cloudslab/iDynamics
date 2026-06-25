#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
scale="${IDYN_SCALE:-scale10}"
profile="${IDYN_REPLICA_PROFILE:-replica1}"

if [[ "${IDYN_GDA_OVERHEAD:-1}" == "1" ]]; then
  exec python3 "$repo_root/scripts/experiments/real_benchmark_gda_overhead.py" \
    --benchmark online-boutique \
    --scale "$scale" \
    --duration "${IDYN_DURATION_SECONDS:-45}" \
    --concurrency "${IDYN_CONCURRENCY:-8}" \
    --samples "${IDYN_GDA_SAMPLES:-7}" \
    --sample-interval "${IDYN_GDA_SAMPLE_INTERVAL:-3}" \
    --window "${IDYN_GDA_WINDOW:-2m}" \
    --loadgenerator-users "${IDYN_USERS:-10}" \
    --loadgenerator-rate "${IDYN_RATE:-5}" \
    ${IDYN_CLEANUP:+--cleanup}
fi

exec python3 "$repo_root/scripts/experiments/online_boutique_external.py" \
  --scale "$scale" \
  --replica-profile "$profile" \
  --duration "${IDYN_DURATION_SECONDS:-45}" \
  --repeats "${IDYN_REPEATS:-3}" \
  --concurrency "${IDYN_CONCURRENCY:-8}" \
  --loadgenerator-users "${IDYN_USERS:-10}" \
  --loadgenerator-rate "${IDYN_RATE:-5}" \
  ${IDYN_CLEANUP:+--cleanup}
