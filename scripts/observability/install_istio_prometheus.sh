#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# shellcheck source=../lib/run_ledger.sh
source "${repo_root}/scripts/lib/run_ledger.sh"

kubectl_bin="${KUBECTL:-kubectl}"
istio_version="${ISTIO_VERSION:-1.30.0}"
run_id="${1:-observability-istio-prometheus-$(date -u +%Y%m%dT%H%M%SZ)}"
run_dir="$(idyn_init_run_ledger "$run_id")"
tools_dir="${repo_root}/.tools"
istio_dir="${tools_dir}/istio-${istio_version}"
lock_file="/tmp/idyn-locks/experiment.lock"

cat >"${run_dir}/config.yaml" <<YAML
run_id: ${run_id}
created_utc: $(idyn_timestamp)
purpose: install_istio_prometheus_observability
mutates_cluster: true
istio_version: ${istio_version}
prometheus_source: istio_sample_addon
physical_scale_claim: none
required_reset_after_run: false
YAML

exec > >(tee "${run_dir}/logs/install_stdout.log") 2> >(tee "${run_dir}/logs/install_stderr.log" >&2)

run_step() {
  idyn_log_command "$run_dir" "$*"
  "$@"
}

capture() {
  local name="$1"
  shift
  idyn_log_command "$run_dir" "$* > ${name}"
  "$@" >"${run_dir}/${name}" 2>"${run_dir}/${name}.err" || true
}

mkdir -p /tmp/idyn-locks "$tools_dir"

(
  flock -n 9 || {
    echo "another live experiment/setup is holding ${lock_file}" >&2
    exit 75
  }

  echo "observability setup run directory: ${run_dir}"
  capture "env/nodes_before.txt" "$kubectl_bin" get nodes -o wide
  capture "env/pods_before.txt" "$kubectl_bin" get pods --all-namespaces -o wide
  capture "env/kubernetes.yaml" "$kubectl_bin" version -o yaml

  if [ ! -x "${istio_dir}/bin/istioctl" ]; then
    echo "downloading Istio ${istio_version} into ${tools_dir}"
    (
      cd "$tools_dir"
      curl -L https://istio.io/downloadIstio | ISTIO_VERSION="$istio_version" TARGET_ARCH=x86_64 sh -
    )
  fi

  run_step "${istio_dir}/bin/istioctl" version --remote=false
  capture "raw/istioctl_local_version.txt" "${istio_dir}/bin/istioctl" version --remote=false

  echo "installing Istio control plane"
  run_step "${istio_dir}/bin/istioctl" install -y --set profile=default

  echo "installing Istio Prometheus addon"
  run_step "$kubectl_bin" apply -f "${istio_dir}/samples/addons/prometheus.yaml"

  echo "waiting for Istio and Prometheus readiness"
  run_step "$kubectl_bin" wait --for=condition=Ready pod --all -n istio-system --timeout=300s
  run_step "$kubectl_bin" rollout status deployment/prometheus -n istio-system --timeout=300s

  capture "raw/istio_system_pods.txt" "$kubectl_bin" get pods -n istio-system -o wide
  capture "raw/istio_system_services.txt" "$kubectl_bin" get svc -n istio-system -o wide
  capture "raw/istio_system_deployments.txt" "$kubectl_bin" get deploy -n istio-system -o wide
  capture "raw/prometheus_version_probe.txt" "$kubectl_bin" exec -n istio-system deploy/prometheus -- prometheus --version
  capture "env/pods_after.txt" "$kubectl_bin" get pods --all-namespaces -o wide

  python3 - "$run_dir" "$istio_version" <<'PY'
import pathlib
import sys

run_dir = pathlib.Path(sys.argv[1])
istio_version = sys.argv[2]
summary = f"""# {run_dir.name}

Status: completed

## Purpose
Install Istio service mesh telemetry and Prometheus metric storage for iDynamics TSC revision experiments.

## Result
- Requested Istio version: {istio_version}
- Prometheus source: Istio sample addon.
- Cluster mutation: installed/updated resources in `istio-system`.

"""
(run_dir / "summary.md").write_text(summary)
PY
  echo "observability setup completed: ${run_dir}"
) 9>"$lock_file"
