#!/usr/bin/env bash
IDYN_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDYN_BENCHMARK_ROOT="$(cd "$IDYN_SCRIPT_DIR/.." && pwd)"
IDYN_REPO_ROOT="$(cd "$IDYN_BENCHMARK_ROOT/../.." && pwd)"
source "$IDYN_REPO_ROOT/benchmarks/_lib/benchmark.sh"

IDYN_BENCHMARK="deathstar-hotel"
IDYN_DISPLAY_NAME="DeathStarBench Hotel Reservation"
IDYN_DEFAULT_NAMESPACE="idyn-dsb-hotel"
IDYN_SOURCE_TYPE="third_party"
IDYN_SOURCE_URL="https://github.com/delimitrou/DeathStarBench.git"
IDYN_SOURCE_COMMIT="6ecb09706140f8730b5385c08f1386c654c3c526"
IDYN_LICENSE="Apache-2.0"
IDYN_EXTERNAL_NAME="deathstarbench"
IDYN_DEPLOY_MODE="kubectl"
IDYN_MANIFEST_PATHS=("hotelReservation/kubernetes")
IDYN_ENTRY_SERVICE="frontend"
IDYN_ENTRY_PORT="5000"
IDYN_ENTRY_PATH="/"
IDYN_LOAD_PATHS=(
  "/"
  "/hotels"
  "/recommendations"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  IDYN_ACTION="configuration"
  idyn::print_help "configuration"
  exit 0
fi
