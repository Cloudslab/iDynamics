#!/usr/bin/env bash
IDYN_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDYN_BENCHMARK_ROOT="$(cd "$IDYN_SCRIPT_DIR/.." && pwd)"
IDYN_REPO_ROOT="$(cd "$IDYN_BENCHMARK_ROOT/../.." && pwd)"
source "$IDYN_REPO_ROOT/benchmarks/_lib/benchmark.sh"

IDYN_BENCHMARK="train-ticket"
IDYN_DISPLAY_NAME="TrainTicket"
IDYN_DEFAULT_NAMESPACE="idyn-train-ticket"
IDYN_SOURCE_TYPE="third_party"
IDYN_SOURCE_URL="https://github.com/FudanSELab/train-ticket.git"
IDYN_SOURCE_COMMIT="313886e99befb94be6cd45f085c98e0019f59829"
IDYN_LICENSE="Apache-2.0"
IDYN_EXTERNAL_NAME="train-ticket"
IDYN_DEPLOY_MODE="kubectl"
IDYN_MANIFEST_PATHS=("deployment/kubernetes-manifests/k8s-with-istio")
IDYN_ENTRY_SERVICE="ts-ui-dashboard"
IDYN_ENTRY_PORT="8080"
IDYN_ENTRY_PATH="/"
IDYN_LOAD_PATHS=(
  "/"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  IDYN_ACTION="configuration"
  idyn::print_help "configuration"
  exit 0
fi
