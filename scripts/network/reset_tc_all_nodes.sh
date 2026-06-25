#!/usr/bin/env bash
set -euo pipefail

kubectl_bin="${KUBECTL:-kubectl}"
namespace="${NAMESPACE:-kube-system}"
interface="${INTERFACE:-auto}"
selector="${NODE_SELECTOR:-!node-role.kubernetes.io/control-plane,!node-role.kubernetes.io/master}"
apply="false"
snapshot_dir=""

usage() {
  cat <<USAGE
Usage: $0 [--apply] [--namespace NAME] [--interface IFACE] [--selector LABEL_SELECTOR] [--snapshot-dir DIR] [--all-nodes]

By default this script prints the nodes that would be touched. Use --apply to
launch one privileged pod per node and delete root and ingress qdiscs.
Use --interface auto to resolve the default-route interface inside each node.
The default node selector excludes control-plane/master nodes.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --apply)
      apply="true"
      shift
      ;;
    --namespace)
      namespace="$2"
      shift 2
      ;;
    --interface)
      interface="$2"
      shift 2
      ;;
    --selector)
      selector="$2"
      shift 2
      ;;
    --snapshot-dir)
      snapshot_dir="$2"
      shift 2
      ;;
    --all-nodes)
      selector=""
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v "$kubectl_bin" >/dev/null 2>&1; then
  echo "kubectl command not found: $kubectl_bin" >&2
  exit 127
fi

if ! "$kubectl_bin" cluster-info >/dev/null 2>&1; then
  echo "kubectl is installed but no reachable cluster is configured; no tc reset performed"
  exit 0
fi

node_args=()
if [ -n "$selector" ]; then
  node_args=(-l "$selector")
fi

mapfile -t nodes < <("$kubectl_bin" get nodes "${node_args[@]}" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort -V)

if [ "${#nodes[@]}" -eq 0 ]; then
  echo "no nodes matched"
  exit 0
fi

printf 'matched nodes:\n'
printf '  %s\n' "${nodes[@]}"

if [ "$apply" != "true" ]; then
  echo "dry run only; re-run with --apply to reset tc qdiscs on $interface"
  exit 0
fi

if [ -z "$snapshot_dir" ]; then
  snapshot_dir="qdisc-before-reset-$(date -u +%Y%m%dT%H%M%SZ)"
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "snapshotting qdisc state before reset into $snapshot_dir"
KUBECTL="$kubectl_bin" NAMESPACE="$namespace" INTERFACE="$interface" NODE_SELECTOR="$selector" \
  "$script_dir/snapshot_qdisc_all_nodes.sh" "$snapshot_dir"

for node in "${nodes[@]}"; do
  pod_name="tc-reset-${node//[^a-zA-Z0-9-]/-}"
  pod_name="${pod_name,,}"
  pod_name="${pod_name:0:50}-$(date +%s)"
  echo "resetting qdiscs on $node:$interface"
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
    "tc qdisc del dev \"$IFACE\" root 2>/dev/null || true; "
    "tc qdisc del dev \"$IFACE\" ingress 2>/dev/null || true; "
    "tc qdisc show dev \"$IFACE\" || true'"
)
print(json.dumps({
    "apiVersion": "v1",
    "spec": {
        "nodeName": node,
        "hostNetwork": True,
        "restartPolicy": "Never",
        "volumes": [{"name": "host-root", "hostPath": {"path": "/", "type": "Directory"}}],
        "containers": [{
            "name": "tc-reset",
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
    --rm=true
done
