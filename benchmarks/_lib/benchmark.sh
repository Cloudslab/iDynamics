# Shared shell helpers for benchmark packaging scripts.

idyn::die() {
  echo "error: $*" >&2
  exit 2
}

idyn::repo_root() {
  local source_dir
  source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$source_dir/../.." && pwd
}

idyn::print_help() {
  local action="$1"
  cat <<EOF
Usage: $0 [OPTIONS]

${IDYN_DISPLAY_NAME:-Benchmark} ${action} helper.

Common options:
  -h, --help                 Show this help text.
  --namespace NAME           Kubernetes namespace. Must start with idyn-.
  --source-root DIR          External checkout root for fetched upstream code.
  --output-dir DIR           Directory for collected metrics or load output.
  --duration SECONDS         Load duration for load/reproduce helpers.
  --concurrency N            Concurrent HTTP clients for load/reproduce helpers.
  --local-port PORT          Local port used for kubectl port-forward.
  --scale LABEL              Optional worker label suffix, e.g. scale45.
  --replica-profile NAME     Optional adapter replica profile name.
  --dry-run                  Print commands without changing the cluster.

Environment:
  IDYN_NAMESPACE             Namespace override.
  IDYN_EXTERNAL_ROOT         External checkout root. Default: external/benchmarks.
  IDYN_CLEANUP=1             Run cleanup after reproduce.
  IDYN_SKIP_FETCH=1          Require an existing source checkout.

Benchmark:
  key:       ${IDYN_BENCHMARK:-unknown}
  namespace: ${IDYN_DEFAULT_NAMESPACE:-unknown}
  source:    ${IDYN_SOURCE_URL:-repository-local}
  commit:    ${IDYN_SOURCE_COMMIT:-not-applicable}
  license:   ${IDYN_LICENSE:-not-specified}
EOF
}

idyn::parse_common_args() {
  IDYN_DRY_RUN="${IDYN_DRY_RUN:-0}"
  IDYN_DURATION_SECONDS="${IDYN_DURATION_SECONDS:-45}"
  IDYN_CONCURRENCY="${IDYN_CONCURRENCY:-4}"
  IDYN_LOCAL_PORT="${IDYN_LOCAL_PORT:-18080}"
  IDYN_REPLICA_PROFILE="${IDYN_REPLICA_PROFILE:-replica1}"
  IDYN_SCALE="${IDYN_SCALE:-}"
  if ! declare -p IDYN_LOAD_PATHS >/dev/null 2>&1; then
    IDYN_LOAD_PATHS=("/")
  fi
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        idyn::print_help "$IDYN_ACTION"
        exit 0
        ;;
      --namespace)
        [[ $# -ge 2 ]] || idyn::die "--namespace requires a value"
        IDYN_NAMESPACE="$2"
        shift 2
        ;;
      --source-root)
        [[ $# -ge 2 ]] || idyn::die "--source-root requires a value"
        IDYN_EXTERNAL_ROOT="$2"
        shift 2
        ;;
      --output-dir)
        [[ $# -ge 2 ]] || idyn::die "--output-dir requires a value"
        IDYN_OUTPUT_DIR="$2"
        shift 2
        ;;
      --duration)
        [[ $# -ge 2 ]] || idyn::die "--duration requires a value"
        IDYN_DURATION_SECONDS="$2"
        shift 2
        ;;
      --concurrency)
        [[ $# -ge 2 ]] || idyn::die "--concurrency requires a value"
        IDYN_CONCURRENCY="$2"
        shift 2
        ;;
      --local-port)
        [[ $# -ge 2 ]] || idyn::die "--local-port requires a value"
        IDYN_LOCAL_PORT="$2"
        shift 2
        ;;
      --scale)
        [[ $# -ge 2 ]] || idyn::die "--scale requires a value"
        IDYN_SCALE="$2"
        shift 2
        ;;
      --replica-profile)
        [[ $# -ge 2 ]] || idyn::die "--replica-profile requires a value"
        IDYN_REPLICA_PROFILE="$2"
        shift 2
        ;;
      --dry-run)
        IDYN_DRY_RUN=1
        shift
        ;;
      *)
        idyn::die "unknown option: $1"
        ;;
    esac
  done
}

idyn::namespace() {
  echo "${IDYN_NAMESPACE:-$IDYN_DEFAULT_NAMESPACE}"
}

idyn::require_safe_namespace() {
  local namespace="$1"
  [[ -n "$namespace" ]] || idyn::die "namespace must not be empty"
  case "$namespace" in
    default|kube-system|kube-public|kube-node-lease|istio-system|monitoring|local-path-storage)
      idyn::die "refusing unsafe namespace: $namespace"
      ;;
  esac
  [[ "$namespace" =~ ^idyn-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || \
    idyn::die "namespace must match idyn-* with lowercase letters, numbers, and hyphens: $namespace"
}

idyn::require_commands() {
  local command
  for command in "$@"; do
    command -v "$command" >/dev/null 2>&1 || idyn::die "missing required command: $command"
  done
}

idyn::run() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if [[ "${IDYN_DRY_RUN:-0}" == "1" ]]; then
    return 0
  fi
  "$@"
}

idyn::source_dir() {
  local root="${IDYN_EXTERNAL_ROOT:-$IDYN_REPO_ROOT/external/benchmarks}"
  echo "$root/${IDYN_EXTERNAL_NAME:-$IDYN_BENCHMARK}"
}

idyn::fetch() {
  [[ "${IDYN_SOURCE_TYPE:-third_party}" == "third_party" ]] || {
    echo "$IDYN_BENCHMARK uses repository-local sources; no upstream fetch is required."
    return 0
  }
  idyn::require_commands git
  [[ -n "${IDYN_SOURCE_URL:-}" ]] || idyn::die "IDYN_SOURCE_URL is not set"
  [[ -n "${IDYN_SOURCE_COMMIT:-}" ]] || idyn::die "IDYN_SOURCE_COMMIT is not set"
  local source_dir parent actual_commit
  source_dir="$(idyn::source_dir)"
  parent="$(dirname "$source_dir")"
  idyn::run mkdir -p "$parent"
  if [[ ! -d "$source_dir/.git" ]]; then
    idyn::run git clone --filter=blob:none "$IDYN_SOURCE_URL" "$source_dir"
  fi
  if [[ "${IDYN_DRY_RUN:-0}" != "1" ]]; then
    git -C "$source_dir" fetch --depth 1 origin "$IDYN_SOURCE_COMMIT" || \
      git -C "$source_dir" fetch origin "$IDYN_SOURCE_COMMIT"
    git -C "$source_dir" checkout --detach "$IDYN_SOURCE_COMMIT"
    actual_commit="$(git -C "$source_dir" rev-parse HEAD)"
    [[ "$actual_commit" == "$IDYN_SOURCE_COMMIT" ]] || \
      idyn::die "checkout commit mismatch: expected $IDYN_SOURCE_COMMIT got $actual_commit"
  else
    idyn::run git -C "$source_dir" checkout --detach "$IDYN_SOURCE_COMMIT"
  fi
  echo "$source_dir"
}

idyn::ensure_source() {
  [[ "${IDYN_SOURCE_TYPE:-third_party}" == "third_party" ]] || return 0
  local source_dir
  source_dir="$(idyn::source_dir)"
  if [[ "${IDYN_SKIP_FETCH:-0}" == "1" ]]; then
    [[ -d "$source_dir" ]] || idyn::die "missing source checkout: $source_dir"
  else
    idyn::fetch >/dev/null
  fi
}

idyn::absolute_source_path() {
  local relative="$1"
  echo "$(idyn::source_dir)/$relative"
}

idyn::create_namespace() {
  local namespace="$1"
  idyn::require_safe_namespace "$namespace"
  idyn::require_commands kubectl
  if [[ "${IDYN_DRY_RUN:-0}" == "1" ]]; then
    idyn::run kubectl create namespace "$namespace" --dry-run=client -o yaml
  else
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
  fi
  idyn::run kubectl label namespace "$namespace" \
    "idynamics.dev/benchmark=$IDYN_BENCHMARK" \
    istio-injection=enabled \
    --overwrite
}

idyn::patch_node_selector() {
  local namespace="$1"
  [[ -n "${IDYN_SCALE:-}" ]] || return 0
  local selector deployment
  selector="{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"idynamics.dev/$IDYN_SCALE\":\"true\"}}}}}"
  while IFS= read -r deployment; do
    [[ -n "$deployment" ]] || continue
    idyn::run kubectl -n "$namespace" patch deployment "$deployment" --type=merge -p "$selector"
  done < <(kubectl -n "$namespace" get deploy -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
}

idyn::deploy_upstream() {
  local namespace="$1"
  idyn::ensure_source
  idyn::create_namespace "$namespace"
  if [[ "${IDYN_DEPLOY_MODE:-kubectl}" == "helm" ]]; then
    idyn::require_commands helm
    local chart
    chart="$(idyn::absolute_source_path "$IDYN_HELM_CHART")"
    [[ -d "$chart" ]] || idyn::die "missing Helm chart: $chart"
    idyn::run helm upgrade --install "${IDYN_RELEASE_NAME:-$IDYN_BENCHMARK}" "$chart" \
      --namespace "$namespace" --create-namespace
  else
    local manifest
    for manifest in "${IDYN_MANIFEST_PATHS[@]}"; do
      local path
      path="$(idyn::absolute_source_path "$manifest")"
      [[ -e "$path" ]] || idyn::die "missing manifest path: $path"
      idyn::run kubectl -n "$namespace" apply -f "$path"
    done
  fi
  idyn::patch_node_selector "$namespace"
  idyn::run kubectl -n "$namespace" rollout status deployment --all --timeout="${IDYN_ROLLOUT_TIMEOUT:-420s}"
}

idyn::deploy_moe() {
  local namespace="$1"
  local experts="${IDYN_MOE_EXPERTS:-4}"
  local cpu_ms="${IDYN_MOE_CPU_MS:-5}"
  idyn::create_namespace "$namespace"
  if [[ "${IDYN_DRY_RUN:-0}" == "1" ]]; then
    idyn::run kubectl -n "$namespace" create configmap moe-serving-app \
      --from-file=server.py="$IDYN_BENCHMARK_ROOT/app/server.py" \
      --dry-run=client -o yaml
  else
    kubectl -n "$namespace" create configmap moe-serving-app \
      --from-file=server.py="$IDYN_BENCHMARK_ROOT/app/server.py" \
      --dry-run=client -o yaml | kubectl apply -f -
  fi
  local service
  for service in frontend tokenizer router aggregator cache; do
    idyn::apply_moe_component "$namespace" "$service" "$service" "$experts" "$cpu_ms"
  done
  local index
  for ((index = 0; index < experts; index++)); do
    idyn::apply_moe_component "$namespace" "expert-$index" expert "$experts" "$cpu_ms"
  done
  idyn::patch_node_selector "$namespace"
  idyn::run kubectl -n "$namespace" rollout status deployment --all --timeout="${IDYN_ROLLOUT_TIMEOUT:-240s}"
}

idyn::apply_moe_component() {
  local namespace="$1"
  local name="$2"
  local role="$3"
  local experts="$4"
  local cpu_ms="$5"
  if [[ "${IDYN_DRY_RUN:-0}" == "1" ]]; then
    echo "would apply MoE component $name in $namespace"
    return 0
  fi
  cat <<EOF | kubectl -n "$namespace" apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $name
  labels:
    app: $name
    idynamics.dev/benchmark: moe-serving
spec:
  replicas: 1
  selector:
    matchLabels:
      app: $name
  template:
    metadata:
      labels:
        app: $name
        idynamics.dev/benchmark: moe-serving
    spec:
      containers:
        - name: app
          image: python:3.11-slim
          imagePullPolicy: IfNotPresent
          command: ["python", "/app/server.py"]
          env:
            - name: ROLE
              value: "$role"
            - name: SERVICE_NAME
              value: "$name"
            - name: EXPERT_COUNT
              value: "$experts"
            - name: CPU_WORK_MS
              value: "$cpu_ms"
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: app
              mountPath: /app
          resources:
            requests:
              cpu: 100m
              memory: 96Mi
            limits:
              cpu: "1"
              memory: 256Mi
      volumes:
        - name: app
          configMap:
            name: moe-serving-app
---
apiVersion: v1
kind: Service
metadata:
  name: $name
  labels:
    app: $name
    idynamics.dev/benchmark: moe-serving
spec:
  selector:
    app: $name
  ports:
    - name: http
      port: 8080
      targetPort: 8080
EOF
}

idyn::deploy() {
  local namespace
  namespace="$(idyn::namespace)"
  if [[ "${IDYN_DEPLOY_MODE:-kubectl}" == "moe-local" ]]; then
    idyn::deploy_moe "$namespace"
  else
    idyn::deploy_upstream "$namespace"
  fi
}

idyn::port_forward() {
  local namespace="$1"
  local service="$2"
  local local_port="$3"
  local remote_port="$4"
  local log_file="${5:-/tmp/idyn-port-forward.log}"
  idyn::require_commands kubectl
  kubectl -n "$namespace" port-forward "svc/$service" "$local_port:$remote_port" --address 127.0.0.1 >"$log_file" 2>&1 &
  IDYN_PF_PID=$!
  trap 'kill "${IDYN_PF_PID:-}" >/dev/null 2>&1 || true' EXIT
  sleep "${IDYN_PORT_FORWARD_WAIT:-3}"
}

idyn::smoke() {
  local namespace url
  namespace="$(idyn::namespace)"
  idyn::require_safe_namespace "$namespace"
  idyn::require_commands kubectl curl
  idyn::run kubectl -n "$namespace" get deploy,svc,pods -o wide
  [[ "${IDYN_DRY_RUN:-0}" == "1" ]] && return 0
  idyn::port_forward "$namespace" "$IDYN_ENTRY_SERVICE" "$IDYN_LOCAL_PORT" "$IDYN_ENTRY_PORT" "/tmp/$IDYN_BENCHMARK-smoke-port-forward.log"
  url="http://127.0.0.1:$IDYN_LOCAL_PORT${IDYN_ENTRY_PATH:-/}"
  local checks="${IDYN_SMOKE_REQUESTS:-3}"
  local i
  for ((i = 1; i <= checks; i++)); do
    curl -fsS "$url" >/dev/null
  done
  echo "$IDYN_BENCHMARK smoke passed: $checks requests to $url"
}

idyn::load() {
  local namespace out_dir output path_args=()
  namespace="$(idyn::namespace)"
  idyn::require_safe_namespace "$namespace"
  idyn::require_commands kubectl python3
  out_dir="${IDYN_OUTPUT_DIR:-$IDYN_REPO_ROOT/experiments/runs/$IDYN_BENCHMARK-manual-load}"
  output="$out_dir/load.csv"
  idyn::run mkdir -p "$out_dir"
  [[ "${IDYN_DRY_RUN:-0}" == "1" ]] && return 0
  idyn::port_forward "$namespace" "$IDYN_ENTRY_SERVICE" "$IDYN_LOCAL_PORT" "$IDYN_ENTRY_PORT" "/tmp/$IDYN_BENCHMARK-load-port-forward.log"
  if [[ ${#IDYN_LOAD_PATHS[@]} -gt 0 ]]; then
    path_args=("--paths" "${IDYN_LOAD_PATHS[*]}")
  fi
  python3 "$IDYN_REPO_ROOT/benchmarks/_lib/http_load.py" \
    --url "http://127.0.0.1:$IDYN_LOCAL_PORT" \
    --duration "$IDYN_DURATION_SECONDS" \
    --concurrency "$IDYN_CONCURRENCY" \
    --output "$output" \
    "${path_args[@]}"
}

idyn::collect() {
  local namespace out_dir
  namespace="$(idyn::namespace)"
  idyn::require_safe_namespace "$namespace"
  idyn::require_commands kubectl
  out_dir="${IDYN_OUTPUT_DIR:-$IDYN_REPO_ROOT/experiments/runs/$IDYN_BENCHMARK-manual-collect}"
  idyn::run mkdir -p "$out_dir"
  [[ "${IDYN_DRY_RUN:-0}" == "1" ]] && return 0
  kubectl -n "$namespace" get pods -o wide >"$out_dir/pods_wide.txt"
  kubectl -n "$namespace" get pods -o json >"$out_dir/pods.json"
  kubectl -n "$namespace" get deploy -o wide >"$out_dir/deployments.txt"
  kubectl -n "$namespace" get svc -o wide >"$out_dir/services.txt"
  kubectl -n "$namespace" get events --sort-by=.lastTimestamp >"$out_dir/events.txt"
  kubectl top nodes >"$out_dir/top_nodes.txt" 2>"$out_dir/top_nodes.err" || true
  kubectl -n "$namespace" top pods >"$out_dir/top_pods.txt" 2>"$out_dir/top_pods.err" || true
  if kubectl -n istio-system get svc prometheus >/dev/null 2>&1; then
    local prom_port="${IDYN_PROM_PORT:-19090}"
    idyn::port_forward istio-system prometheus "$prom_port" 9090 "$out_dir/prometheus-port-forward.log"
    local query
    query="sum(rate(istio_requests_total{destination_workload_namespace=\"$namespace\"}[2m])) by (source_workload,destination_workload,response_code)"
    if command -v curl >/dev/null 2>&1; then
      curl -fsS --get --data-urlencode "query=$query" "http://127.0.0.1:$prom_port/api/v1/query" >"$out_dir/istio_requests.json" || true
    fi
  fi
  echo "$out_dir"
}

idyn::cleanup() {
  local namespace
  namespace="$(idyn::namespace)"
  idyn::require_safe_namespace "$namespace"
  idyn::require_commands kubectl
  if [[ "${IDYN_DEPLOY_MODE:-kubectl}" == "helm" ]]; then
    if command -v helm >/dev/null 2>&1; then
      idyn::run helm uninstall "${IDYN_RELEASE_NAME:-$IDYN_BENCHMARK}" --namespace "$namespace" --ignore-not-found || true
    fi
  fi
  idyn::run kubectl delete namespace "$namespace" --ignore-not-found=true
}

idyn::reproduce() {
  idyn::deploy
  idyn::smoke
  idyn::load
  idyn::collect
  if [[ "${IDYN_CLEANUP:-0}" == "1" ]]; then
    idyn::cleanup
  fi
}

idyn::dispatch() {
  IDYN_ACTION="$1"
  shift
  idyn::parse_common_args "$@"
  case "$IDYN_ACTION" in
    fetch) idyn::fetch ;;
    deploy) idyn::deploy ;;
    smoke) idyn::smoke ;;
    load) idyn::load ;;
    collect) idyn::collect ;;
    cleanup) idyn::cleanup ;;
    reproduce) idyn::reproduce ;;
    *) idyn::die "unknown action: $IDYN_ACTION" ;;
  esac
}
