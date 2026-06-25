#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-train-ticket}"
manifest="${TRAIN_TICKET_MANIFEST:-/home/ubuntu/idyn-external/train-ticket/deployment/kubernetes-manifests/k8s-with-istio}"
scale="${IDYN_SCALE:-}"

if [[ ! -e "$manifest" ]]; then
  echo "missing TrainTicket manifest path: $manifest" >&2
  exit 2
fi

kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$namespace" istio-injection="${IDYN_ISTIO_INJECTION:-enabled}" --overwrite
kubectl -n "$namespace" apply -f "$manifest"

if [[ -n "$scale" ]]; then
  selector="{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"idynamics.dev/$scale\":\"true\"}}}}}"
  for deploy in $(kubectl -n "$namespace" get deploy -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null); do
    kubectl -n "$namespace" patch deployment "$deploy" --type=merge -p "$selector" || true
  done
fi

kubectl -n "$namespace" rollout status deployment --all --timeout="${IDYN_ROLLOUT_TIMEOUT:-600s}" || true
