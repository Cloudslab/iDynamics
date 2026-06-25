#!/usr/bin/env bash
set -euo pipefail

kubectl_bin="${KUBECTL:-kubectl}"
namespace="${NAMESPACE:-kube-system}"
interface="${INTERFACE:-auto}"
selector="${NODE_SELECTOR:-!node-role.kubernetes.io/control-plane,!node-role.kubernetes.io/master}"
out_dir="${1:-qdisc-snapshot-$(date -u +%Y%m%dT%H%M%SZ)}"

usage() {
  cat <<USAGE
Usage: $0 [OUTPUT_DIR]

Snapshots tc qdisc/class/filter state on worker nodes by default.

Environment:
  KUBECTL        kubectl binary, default: kubectl
  NAMESPACE      helper pod namespace, default: kube-system
  INTERFACE      interface name or auto, default: auto
  NODE_SELECTOR  node selector, default: workers only
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

mkdir -p "$out_dir"

if ! command -v "$kubectl_bin" >/dev/null 2>&1; then
  echo "kubectl command not found: $kubectl_bin" | tee "$out_dir/status.txt"
  exit 0
fi

if ! "$kubectl_bin" cluster-info >/dev/null 2>&1; then
  echo "kubectl is installed but no reachable cluster is configured" | tee "$out_dir/status.txt"
  exit 0
fi

node_args=()
if [ -n "$selector" ]; then
  node_args=(-l "$selector")
fi

mapfile -t nodes < <("$kubectl_bin" get nodes "${node_args[@]}" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort -V)

if [ "${#nodes[@]}" -eq 0 ]; then
  echo "no nodes matched" | tee "$out_dir/status.txt"
  exit 0
fi

printf '%s\n' "${nodes[@]}" >"$out_dir/nodes.txt"

for node in "${nodes[@]}"; do
  pod_name="tc-snapshot-${node//[^a-zA-Z0-9-]/-}"
  pod_name="${pod_name,,}"
  pod_name="${pod_name:0:45}-$(date +%s)"
  target="$out_dir/${node//[^a-zA-Z0-9_.-]/-}.txt"
  echo "snapshotting qdisc on $node" | tee -a "$out_dir/status.txt"
  overrides="$(
    NODE_NAME="$node" IFACE_NAME="$interface" python3 - <<'PY'
import json
import os

node = os.environ["NODE_NAME"]
iface = os.environ["IFACE_NAME"]
script = (
    "chroot /host /bin/sh -c '"
    f"IFACE={iface}; "
    "if [ \"$IFACE\" = auto ]; then IFACE=$(ip route get 1.1.1.1 | "
    "awk '\\''{for(i=1;i<=NF;i++) if($i==\"dev\") print $(i+1)}'\\'' | head -1); fi; "
    "echo IFACE=$IFACE; "
    "tc qdisc show dev \"$IFACE\" || true; "
    "tc class show dev \"$IFACE\" || true; "
    "tc filter show dev \"$IFACE\" || true'"
)
print(json.dumps({
    "apiVersion": "v1",
    "spec": {
        "nodeName": node,
        "hostNetwork": True,
        "restartPolicy": "Never",
        "volumes": [{"name": "host-root", "hostPath": {"path": "/", "type": "Directory"}}],
        "containers": [{
            "name": "tc-snapshot",
            "image": "ubuntu:22.04",
            "securityContext": {"privileged": True},
            "command": ["/bin/sh", "-c", script],
            "volumeMounts": [{"name": "host-root", "mountPath": "/host"}],
        }],
    },
}))
PY
  )"
  "$kubectl_bin" run "$pod_name" \
    --namespace "$namespace" \
    --restart=Never \
    --image=ubuntu:22.04 \
    --overrides "$overrides" \
    --attach=true \
    --rm=true >"$target" 2>"$target.err" || true
done
