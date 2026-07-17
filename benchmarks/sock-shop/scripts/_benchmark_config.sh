#!/usr/bin/env bash
IDYN_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDYN_BENCHMARK_ROOT="$(cd "$IDYN_SCRIPT_DIR/.." && pwd)"
IDYN_REPO_ROOT="$(cd "$IDYN_BENCHMARK_ROOT/../.." && pwd)"
source "$IDYN_REPO_ROOT/benchmarks/_lib/benchmark.sh"

IDYN_BENCHMARK="sock-shop"
IDYN_DISPLAY_NAME="Sock Shop"
IDYN_DEFAULT_NAMESPACE="idyn-sock-shop"
IDYN_SOURCE_TYPE="third_party"
IDYN_SOURCE_URL="https://github.com/microservices-demo/microservices-demo.git"
IDYN_SOURCE_COMMIT="9dff06fae4981921caec6a62393a6ebfce4b3e3f"
IDYN_LICENSE="Apache-2.0"
IDYN_EXTERNAL_NAME="sock-shop"
IDYN_DEPLOY_MODE="kubectl"
IDYN_MANIFEST_PATHS=(
  "deploy/kubernetes/manifests"
  "deploy/kubernetes/manifests-loadtest"
)
IDYN_ENTRY_SERVICE="front-end"
IDYN_ENTRY_PORT="80"
IDYN_ENTRY_PATH="/"
IDYN_LOAD_PATHS=(
  "/"
  "/catalogue"
  "/basket.html"
  "/login"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  IDYN_ACTION="configuration"
  idyn::print_help "configuration"
  exit 0
fi
