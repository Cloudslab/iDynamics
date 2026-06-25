#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "$repo_root/scripts/lib/run_ledger.sh"

timestamp="$(idyn_timestamp)"
run_id="${RUN_ID:-moe-serving-${timestamp}}"
experts="${MOE_EXPERTS:-6}"
steps="${MOE_STEPS:-48}"
requests_per_step="${MOE_REQUESTS_PER_STEP:-60}"
nodes="${MOE_NODES:-5}"
top_k="${MOE_TOP_K:-2}"
skew_mode="${MOE_SKEW_MODE:-phase-shift}"
zipf_alpha="${MOE_ZIPF_ALPHA:-1.2}"
compute_delay_ms="${MOE_COMPUTE_DELAY_MS:-5}"
payload_bytes="${MOE_PAYLOAD_BYTES:-256}"
cache_hit_ratio="${MOE_CACHE_HIT_RATIO:-0.25}"
policies="${MOE_POLICIES:-default policy2 policy3 policy4}"
scale_label="${MOE_SCALE_LABEL:-}"
seed="${MOE_SEED:-23}"
image="${MOE_IMAGE:-moe-serving:latest}"
live_k8s="${MOE_LIVE_K8S:-0}"

config_file="$(mktemp)"
cat >"$config_file" <<YAML
run_id: ${run_id}
created_utc: ${timestamp}
purpose: application_generality_moe_serving
physical_scale_claim: none
experts: ${experts}
steps: ${steps}
requests_per_step: ${requests_per_step}
nodes: ${nodes}
top_k: ${top_k}
skew_mode: ${skew_mode}
zipf_alpha: ${zipf_alpha}
compute_delay_ms: ${compute_delay_ms}
payload_bytes: ${payload_bytes}
cache_hit_ratio: ${cache_hit_ratio}
policies: [${policies// /, }]
scale_label: ${scale_label}
seed: ${seed}
image: ${image}
live_k8s: ${live_k8s}
YAML

run_dir="$(idyn_init_run_ledger "$run_id" "$config_file")"
rm -f "$config_file"

idyn_log_command "$run_dir" "$0"

{
  date -u
  uname -a
  python3 --version
  kubectl version --client=true 2>/dev/null || true
  find /home/ubuntu -maxdepth 3 -type d \( -iname '*DeathStarBench*' -o -iname '*TrainTicket*' -o -iname '*hotel*' -o -iname '*media*' \) 2>/dev/null | sort || true
} >"$run_dir/env/host_metadata.txt" 2>"$run_dir/env/host_metadata.txt.err" || true

{
  kubectl get nodes -o wide 2>/dev/null || true
  kubectl get pods -A -o wide 2>/dev/null || true
} >"$run_dir/env/kubernetes_snapshot.txt" 2>"$run_dir/env/kubernetes_snapshot.txt.err" || true

args=(
  "$repo_root/scripts/experiments/moe_serving_experiment.py"
  --run-dir "$run_dir"
  --experts "$experts"
  --steps "$steps"
  --requests-per-step "$requests_per_step"
  --nodes "$nodes"
  --top-k "$top_k"
  --skew-mode "$skew_mode"
  --zipf-alpha "$zipf_alpha"
  --compute-delay-ms "$compute_delay_ms"
  --payload-bytes "$payload_bytes"
  --cache-hit-ratio "$cache_hit_ratio"
  --seed "$seed"
  --image "$image"
)

read -r -a policy_args <<<"$policies"
args+=(--policies "${policy_args[@]}")

if [ -n "$scale_label" ]; then
  args+=(--scale-label "$scale_label")
fi

if [ "$live_k8s" = "1" ]; then
  args+=(--live-k8s)
fi

idyn_log_command "$run_dir" "python3 ${args[*]}"
PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" python3 "${args[@]}" \
  >"$run_dir/logs/moe_serving_stdout.log" \
  2>"$run_dir/logs/moe_serving_stderr.log"

printf '%s\n' "$run_dir"
