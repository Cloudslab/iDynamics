#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "$repo_root/scripts/lib/run_ledger.sh"

timestamp="$(idyn_timestamp)"
run_id="${RUN_ID:-network-trace-${timestamp}}"
nodes="${NETWORK_TRACE_NODES:-5}"
steps="${NETWORK_TRACE_STEPS:-36}"
interval_s="${NETWORK_TRACE_INTERVAL_S:-5}"
seed="${NETWORK_TRACE_SEED:-21}"
apply_tc="${NETWORK_TRACE_APPLY_TC:-0}"

config_file="$(mktemp)"
cat >"$config_file" <<YAML
run_id: ${run_id}
created_utc: ${timestamp}
purpose: network_trace_replay_and_burst_correlation
physical_scale_claim: none
nodes: ${nodes}
steps: ${steps}
interval_s: ${interval_s}
seed: ${seed}
tc_apply: ${apply_tc}
YAML

run_dir="$(idyn_init_run_ledger "$run_id" "$config_file")"
rm -f "$config_file"

idyn_log_command "$run_dir" "$0"

{
  date -u
  uname -a
  python3 --version
  kubectl version --client=true 2>/dev/null || true
} >"$run_dir/env/host_metadata.txt" 2>"$run_dir/env/host_metadata.txt.err" || true

idyn_log_command "$run_dir" "scripts/network/snapshot_qdisc_all_nodes.sh $run_dir/env/qdisc_before"
"$repo_root/scripts/network/snapshot_qdisc_all_nodes.sh" "$run_dir/env/qdisc_before" \
  >"$run_dir/logs/qdisc_before_stdout.log" 2>"$run_dir/logs/qdisc_before_stderr.log" || true

idyn_log_command "$run_dir" "python3 scripts/experiments/network_trace_replay.py --run-dir $run_dir --nodes $nodes --steps $steps --interval-s $interval_s --seed $seed"
PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" python3 "$repo_root/scripts/experiments/network_trace_replay.py" \
  --run-dir "$run_dir" \
  --nodes "$nodes" \
  --steps "$steps" \
  --interval-s "$interval_s" \
  --seed "$seed" \
  >"$run_dir/logs/network_trace_replay_stdout.log" \
  2>"$run_dir/logs/network_trace_replay_stderr.log"

if [ "$apply_tc" = "1" ]; then
  cat >"$run_dir/logs/tc_apply_notice.log" <<'LOG'
NETWORK_TRACE_APPLY_TC=1 was requested, but this target currently archives replayable
matrices and metrics only. Live frame-by-frame qdisc application should be run through
a separate guarded injector after selecting node IPs and interfaces.
LOG
fi

idyn_log_command "$run_dir" "scripts/network/reset_tc_all_nodes.sh --apply"
"$repo_root/scripts/network/reset_tc_all_nodes.sh" --apply \
  >"$run_dir/logs/tc_reset_stdout.log" 2>"$run_dir/logs/tc_reset_stderr.log" || true

idyn_log_command "$run_dir" "scripts/network/snapshot_qdisc_all_nodes.sh $run_dir/env/qdisc_after"
"$repo_root/scripts/network/snapshot_qdisc_all_nodes.sh" "$run_dir/env/qdisc_after" \
  >"$run_dir/logs/qdisc_after_stdout.log" 2>"$run_dir/logs/qdisc_after_stderr.log" || true

printf '%s\n' "$run_dir"
