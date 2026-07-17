#!/usr/bin/env bash
IDYN_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDYN_BENCHMARK_ROOT="$(cd "$IDYN_SCRIPT_DIR/.." && pwd)"
IDYN_REPO_ROOT="$(cd "$IDYN_BENCHMARK_ROOT/../.." && pwd)"
source "$IDYN_REPO_ROOT/benchmarks/_lib/benchmark.sh"

IDYN_BENCHMARK="social-network"
IDYN_DISPLAY_NAME="DeathStarBench Social Network"
IDYN_DEFAULT_NAMESPACE="idyn-social-network"
IDYN_SOURCE_TYPE="third_party"
IDYN_SOURCE_URL="https://github.com/delimitrou/DeathStarBench.git"
IDYN_SOURCE_COMMIT="6ecb09706140f8730b5385c08f1386c654c3c526"
IDYN_LICENSE="Apache-2.0"
IDYN_EXTERNAL_NAME="deathstarbench"
IDYN_DEPLOY_MODE="helm"
IDYN_HELM_CHART="socialNetwork/helm-chart/socialnetwork"
IDYN_RELEASE_NAME="social-network"
IDYN_ENTRY_SERVICE="nginx-thrift"
IDYN_ENTRY_PORT="8080"
IDYN_ENTRY_PATH="/wrk2-api/home-timeline/read"
IDYN_LOAD_PATHS=(
  "/wrk2-api/home-timeline/read"
  "/wrk2-api/user-timeline/read"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  IDYN_ACTION="configuration"
  idyn::print_help "configuration"
  exit 0
fi
