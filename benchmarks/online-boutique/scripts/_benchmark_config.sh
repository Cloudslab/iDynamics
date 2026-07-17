#!/usr/bin/env bash
IDYN_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDYN_BENCHMARK_ROOT="$(cd "$IDYN_SCRIPT_DIR/.." && pwd)"
IDYN_REPO_ROOT="$(cd "$IDYN_BENCHMARK_ROOT/../.." && pwd)"
source "$IDYN_REPO_ROOT/benchmarks/_lib/benchmark.sh"

IDYN_BENCHMARK="online-boutique"
IDYN_DISPLAY_NAME="Online Boutique / Google Microservices Demo"
IDYN_DEFAULT_NAMESPACE="idyn-online-boutique"
IDYN_SOURCE_TYPE="third_party"
IDYN_SOURCE_URL="https://github.com/GoogleCloudPlatform/microservices-demo.git"
IDYN_SOURCE_COMMIT="5096a85b2f3bf41bef53363cfe5478d5b86ac701"
IDYN_LICENSE="Apache-2.0"
IDYN_EXTERNAL_NAME="online-boutique"
IDYN_DEPLOY_MODE="kubectl"
IDYN_MANIFEST_PATHS=("release/kubernetes-manifests.yaml")
IDYN_ENTRY_SERVICE="frontend"
IDYN_ENTRY_PORT="80"
IDYN_ENTRY_PATH="/"
IDYN_LOAD_PATHS=(
  "/"
  "/product/0PUK6V6EV0"
  "/product/2ZYFJ3GM2N"
  "/cart"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  IDYN_ACTION="configuration"
  idyn::print_help "configuration"
  exit 0
fi
