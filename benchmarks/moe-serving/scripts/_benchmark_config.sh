#!/usr/bin/env bash
IDYN_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDYN_BENCHMARK_ROOT="$(cd "$IDYN_SCRIPT_DIR/.." && pwd)"
IDYN_REPO_ROOT="$(cd "$IDYN_BENCHMARK_ROOT/../.." && pwd)"
source "$IDYN_REPO_ROOT/benchmarks/_lib/benchmark.sh"

IDYN_BENCHMARK="moe-serving"
IDYN_DISPLAY_NAME="CPU-only MoE Serving Microbenchmark"
IDYN_DEFAULT_NAMESPACE="idyn-moe-serving"
IDYN_SOURCE_TYPE="repository_local"
IDYN_LICENSE="Repository package metadata: MIT"
IDYN_DEPLOY_MODE="moe-local"
IDYN_ENTRY_SERVICE="frontend"
IDYN_ENTRY_PORT="8080"
IDYN_ENTRY_PATH="/infer?request_type=multi_expert_top2&top_k=2&payload_bytes=1024"
IDYN_LOAD_PATHS=(
  "/infer?request_type=single_expert&top_k=1&payload_bytes=256"
  "/infer?request_type=multi_expert_top2&top_k=2&payload_bytes=1024"
  "/infer?request_type=multi_expert_top4&top_k=4&payload_bytes=2048"
  "/infer?request_type=cache_hit&top_k=1&cache_intent=hit"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  IDYN_ACTION="configuration"
  idyn::print_help "configuration"
  exit 0
fi
