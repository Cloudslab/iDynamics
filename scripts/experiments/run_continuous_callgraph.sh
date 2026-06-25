#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "$repo_root/scripts/lib/run_ledger.sh"

timestamp="$(idyn_timestamp)"
run_id="${RUN_ID:-continuous-callgraph-${timestamp}}"
mode="${CONTINUOUS_CALLGRAPH_MODE:-sinusoidal}"
steps="${CONTINUOUS_CALLGRAPH_STEPS:-48}"
interval_s="${CONTINUOUS_CALLGRAPH_INTERVAL_S:-5}"
total_qps="${CONTINUOUS_CALLGRAPH_TOTAL_QPS:-90}"
seed="${CONTINUOUS_CALLGRAPH_SEED:-31}"
live_wrk="${CONTINUOUS_CALLGRAPH_LIVE_WRK:-0}"
trace_csv="${CONTINUOUS_CALLGRAPH_TRACE_CSV:-}"
scale="${CONTINUOUS_CALLGRAPH_SCALE:-synthetic}"
policies="${CONTINUOUS_CALLGRAPH_POLICIES:-kubernetes-default,cga,hda}"
base_url="${CONTINUOUS_CALLGRAPH_BASE_URL:-http://nginx-thrift.social-network.svc.cluster.local:8080}"
wrk_bin="${CONTINUOUS_CALLGRAPH_WRK_BIN:-/home/ubuntu/DeathStarBench/wrk2/wrk}"
benchmark="${CONTINUOUS_CALLGRAPH_BENCHMARK:-social-network}"
namespace="${CONTINUOUS_CALLGRAPH_NAMESPACE:-social-network}"
replica_level="${CONTINUOUS_CALLGRAPH_REPLICA_LEVEL:-}"
replica_config="${CONTINUOUS_CALLGRAPH_REPLICA_CONFIG:-}"
repeat="${CONTINUOUS_CALLGRAPH_REPEAT:-}"
worker_nodes_selected="${CONTINUOUS_CALLGRAPH_WORKER_NODES_SELECTED:-}"
actual_app_pods="${CONTINUOUS_CALLGRAPH_ACTUAL_APP_PODS:-}"
ready_app_pods="${CONTINUOUS_CALLGRAPH_READY_APP_PODS:-}"
non_empty_worker_nodes="${CONTINUOUS_CALLGRAPH_NON_EMPTY_WORKER_NODES:-}"
pod_restarts="${CONTINUOUS_CALLGRAPH_POD_RESTARTS:-}"
total_pods="${CONTINUOUS_CALLGRAPH_TOTAL_PODS:-}"

config_file="$(mktemp)"
cat >"$config_file" <<YAML
run_id: ${run_id}
created_utc: ${timestamp}
purpose: continuous_callgraph_workload_mix
physical_scale_claim: none
mode: ${mode}
steps: ${steps}
interval_s: ${interval_s}
total_qps: ${total_qps}
seed: ${seed}
live_wrk: ${live_wrk}
trace_csv: ${trace_csv}
scale: ${scale}
policies: ${policies}
base_url: ${base_url}
wrk_bin: ${wrk_bin}
benchmark: ${benchmark}
namespace: ${namespace}
replica_level: ${replica_level}
replica_config: ${replica_config}
repeat: ${repeat}
worker_nodes_selected: ${worker_nodes_selected}
actual_app_pods: ${actual_app_pods}
ready_app_pods: ${ready_app_pods}
non_empty_worker_nodes: ${non_empty_worker_nodes}
pod_restarts: ${pod_restarts}
total_pods: ${total_pods}
YAML

run_dir="$(idyn_init_run_ledger "$run_id" "$config_file")"
rm -f "$config_file"

idyn_log_command "$run_dir" "$0"

cat >"$run_dir/reproduce.sh" <<SH
#!/usr/bin/env bash
set -euo pipefail

repo_root="\$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export RUN_ID="\${RUN_ID:-${run_id}}"
export CONTINUOUS_CALLGRAPH_MODE="${mode}"
export CONTINUOUS_CALLGRAPH_STEPS="${steps}"
export CONTINUOUS_CALLGRAPH_INTERVAL_S="${interval_s}"
export CONTINUOUS_CALLGRAPH_TOTAL_QPS="${total_qps}"
export CONTINUOUS_CALLGRAPH_SEED="${seed}"
export CONTINUOUS_CALLGRAPH_LIVE_WRK="${live_wrk}"
export CONTINUOUS_CALLGRAPH_TRACE_CSV="${trace_csv}"
export CONTINUOUS_CALLGRAPH_SCALE="${scale}"
export CONTINUOUS_CALLGRAPH_POLICIES="${policies}"
export CONTINUOUS_CALLGRAPH_BASE_URL="${base_url}"
export CONTINUOUS_CALLGRAPH_WRK_BIN="${wrk_bin}"
export CONTINUOUS_CALLGRAPH_BENCHMARK="${benchmark}"
export CONTINUOUS_CALLGRAPH_NAMESPACE="${namespace}"
export CONTINUOUS_CALLGRAPH_REPLICA_LEVEL="${replica_level}"
export CONTINUOUS_CALLGRAPH_REPLICA_CONFIG="${replica_config}"
export CONTINUOUS_CALLGRAPH_REPEAT="${repeat}"
export CONTINUOUS_CALLGRAPH_WORKER_NODES_SELECTED="${worker_nodes_selected}"
export CONTINUOUS_CALLGRAPH_ACTUAL_APP_PODS="${actual_app_pods}"
export CONTINUOUS_CALLGRAPH_READY_APP_PODS="${ready_app_pods}"
export CONTINUOUS_CALLGRAPH_NON_EMPTY_WORKER_NODES="${non_empty_worker_nodes}"
export CONTINUOUS_CALLGRAPH_POD_RESTARTS="${pod_restarts}"
export CONTINUOUS_CALLGRAPH_TOTAL_PODS="${total_pods}"

"\$repo_root/scripts/experiments/run_continuous_callgraph.sh"
SH
chmod +x "$run_dir/reproduce.sh"

{
  date -u
  uname -a
  python3 --version
  kubectl version --client=true 2>/dev/null || true
  if command -v "$wrk_bin" >/dev/null 2>&1; then
    "$wrk_bin" --version 2>&1 || true
  else
    echo "wrk binary not found at $wrk_bin"
  fi
} >"$run_dir/env/host_metadata.txt" 2>"$run_dir/env/host_metadata.txt.err" || true

{
  kubectl get nodes -o wide 2>/dev/null || true
  kubectl get pods -A -o wide 2>/dev/null || true
} >"$run_dir/env/kubernetes_snapshot.txt" 2>"$run_dir/env/kubernetes_snapshot.txt.err" || true

args=(
  "$repo_root/scripts/experiments/continuous_callgraph.py"
  --run-dir "$run_dir"
  --mode "$mode"
  --steps "$steps"
  --interval-s "$interval_s"
  --total-qps "$total_qps"
  --seed "$seed"
  --base-url "$base_url"
  --wrk-bin "$wrk_bin"
  --scale "$scale"
  --policies "$policies"
  --benchmark "$benchmark"
  --namespace "$namespace"
  --replica-level "$replica_level"
  --replica-config "$replica_config"
  --repeat "$repeat"
  --worker-nodes-selected "$worker_nodes_selected"
  --actual-app-pods "$actual_app_pods"
  --ready-app-pods "$ready_app_pods"
  --non-empty-worker-nodes "$non_empty_worker_nodes"
  --pod-restarts "$pod_restarts"
  --total-pods "$total_pods"
)

if [ -n "$trace_csv" ]; then
  args+=(--trace-csv "$trace_csv")
fi

if [ "$live_wrk" = "1" ]; then
  args+=(--live-wrk)
fi

idyn_log_command "$run_dir" "python3 ${args[*]}"
PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" python3 "${args[@]}" \
  >"$run_dir/logs/continuous_callgraph_stdout.log" \
  2>"$run_dir/logs/continuous_callgraph_stderr.log"

PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" python3 "$repo_root/scripts/evaluation/summarize_continuous_longmix.py" \
  --run-dir "$run_dir" \
  >>"$run_dir/logs/continuous_callgraph_stdout.log" \
  2>>"$run_dir/logs/continuous_callgraph_stderr.log"

PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" python3 "$repo_root/scripts/evaluation/plot_continuous_longmix.py" \
  --run-dir "$run_dir" \
  >>"$run_dir/logs/continuous_callgraph_stdout.log" \
  2>>"$run_dir/logs/continuous_callgraph_stderr.log"

printf '%s\n' "$run_dir"
