#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# shellcheck source=../lib/run_ledger.sh
source "${repo_root}/scripts/lib/run_ledger.sh"

run_id="${1:-gda-scalability-synth-$(date -u +%Y%m%dT%H%M%SZ)}"
run_dir="$(idyn_init_run_ledger "$run_id")"
sizes="${GDA_SIZES:-50,100,250,500,1000,5000}"
edge_factor="${GDA_EDGE_FACTOR:-4}"
repetitions="${GDA_REPETITIONS:-7}"
dense_pairwise="${GDA_DENSE_PAIRWISE:-true}"
dense_max_services="${GDA_DENSE_MAX_SERVICES:-1000}"
replicas="${GDA_REPLICAS:-1}"
scrape_interval_seconds="${GDA_SCRAPE_INTERVAL_SECONDS:-15}"
prometheus_query_latency_ms="${GDA_PROMETHEUS_QUERY_LATENCY_MS:-0}"

cat >"${run_dir}/config.yaml" <<YAML
run_id: ${run_id}
created_utc: $(idyn_timestamp)
purpose: synthetic_sparse_gda_scalability_overhead
mutates_cluster: false
sizes: [${sizes}]
edge_factor: ${edge_factor}
repetitions: ${repetitions}
dense_pairwise: ${dense_pairwise}
dense_max_services: ${dense_max_services}
replicas: ${replicas}
scrape_interval_seconds: ${scrape_interval_seconds}
prometheus_query_latency_ms: ${prometheus_query_latency_ms}
physical_scale_claim: none_synthetic_control_plane_only
YAML

idyn_log_command "$run_dir" "scripts/experiments/run_gda_overhead_synthetic.sh ${run_id}"

{
  date -u
  uname -a
  python3 --version
  git -C "$repo_root" rev-parse HEAD 2>/dev/null || true
  git -C "$repo_root" status --short --branch 2>/dev/null || true
} >"${run_dir}/env/host_metadata.txt" 2>"${run_dir}/env/host_metadata.txt.err" || true

profile_cmd=(python3 "${repo_root}/scripts/experiments/profile_gda_overhead.py"
  --run-dir "$run_dir" \
  --sizes "$sizes" \
  --edge-factor "$edge_factor" \
  --repetitions "$repetitions" \
  --replicas "$replicas" \
  --scrape-interval-seconds "$scrape_interval_seconds" \
  --prometheus-query-latency-ms "$prometheus_query_latency_ms" \
  --dense-max-services "$dense_max_services")
if [ "$dense_pairwise" = "true" ]; then
  profile_cmd+=(--dense-pairwise)
fi

idyn_log_command "$run_dir" "${profile_cmd[*]}"
"${profile_cmd[@]}" \
  >"${run_dir}/logs/profile_stdout.log" \
  2>"${run_dir}/logs/profile_stderr.log"

cp "${run_dir}/processed/gda_overhead_summary.csv" "${run_dir}/raw/gda_overhead_summary_copy.csv"

python3 "${repo_root}/scripts/evaluation/collect_metrics.py" --run-id "$run_id" >>"${run_dir}/logs/profile_stdout.log" 2>>"${run_dir}/logs/profile_stderr.log" || true
python3 "${repo_root}/scripts/evaluation/summarize_run.py" --run-id "$run_id" --refresh >>"${run_dir}/logs/profile_stdout.log" 2>>"${run_dir}/logs/profile_stderr.log" || true


echo "GDA overhead synthetic run completed: ${run_dir}"
