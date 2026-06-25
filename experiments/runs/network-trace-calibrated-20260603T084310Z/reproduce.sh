#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
run_id="${RUN_ID:-network-trace-calibrated-20260603T084310Z}"
measurement_id="${NETWORK_TRACE_MEASUREMENT_ID:-1001}"
probe_count="${NETWORK_TRACE_PROBE_COUNT:-12}"
window_hours="${NETWORK_TRACE_WINDOW_HOURS:-24.0}"
timeout_s="${NETWORK_TRACE_TIMEOUT_S:-60}"
seed="${NETWORK_TRACE_SEED:-46}"

python3 "$repo_root/scripts/experiments/calibrate_network_trace.py" \
  --run-id "$run_id" \
  --measurement-id "$measurement_id" \
  --probe-count "$probe_count" \
  --window-hours "$window_hours" \
  --timeout-s "$timeout_s" \
  --seed "$seed"
