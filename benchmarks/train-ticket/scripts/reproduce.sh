#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

exec python3 "$repo_root/scripts/experiments/real_benchmark_gda_overhead.py" \
  --benchmark train-ticket \
  --scale "${IDYN_SCALE:-scale45}" \
  --duration "${IDYN_DURATION_SECONDS:-45}" \
  --concurrency "${IDYN_CONCURRENCY:-8}" \
  --samples "${IDYN_GDA_SAMPLES:-7}" \
  --sample-interval "${IDYN_GDA_SAMPLE_INTERVAL:-3}" \
  --window "${IDYN_GDA_WINDOW:-2m}" \
  ${IDYN_CLEANUP:+--cleanup}
