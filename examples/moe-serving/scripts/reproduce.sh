#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

scale="${MOE_SCALE:-scale10}"
skews="${MOE_SKEWS:-phase_shift markov}"
requests="${MOE_REQUESTS:-120}"
qps="${MOE_QPS:-10}"
experts="${MOE_EXPERTS:-6}"
top_k="${MOE_TOP_K:-2}"
compute_delay_ms="${MOE_COMPUTE_DELAY_MS:-5}"
payload_bytes="${MOE_PAYLOAD_BYTES:-256}"
image="${MOE_IMAGE:-python:3.11-slim}"

for skew in $skews; do
  run_id="moe-live-${scale}-${skew//_/-}-$(date -u +%Y%m%dT%H%M%SZ)"
  PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" \
    python3 "$repo_root/scripts/experiments/run_physical_moe_k8s.py" \
      --scale "$scale" \
      --run-id "$run_id" \
      --experts "$experts" \
      --requests "$requests" \
      --qps "$qps" \
      --top-k "$top_k" \
      --skew-mode "$skew" \
      --compute-delay-ms "$compute_delay_ms" \
      --payload-bytes "$payload_bytes" \
      --image "$image"
done
