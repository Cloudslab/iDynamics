#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-sock-shop}"
manifest="${SOCK_SHOP_MANIFEST:-/home/ubuntu/idyn-external/sock-shop/deploy/kubernetes/manifests}"
scale="${IDYN_SCALE:-}"

if [[ ! -e "$manifest" ]]; then
  echo "missing Sock Shop manifest path: $manifest" >&2
  exit 2
fi

kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$namespace" istio-injection="${IDYN_ISTIO_INJECTION:-enabled}" --overwrite
kubectl -n "$namespace" apply -f "$manifest"

if [[ -n "$scale" ]]; then
  selector="{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"idynamics.dev/$scale\":\"true\"}}}}}"
  for deploy in front-end catalogue carts orders payment queue-master shipping user; do
    kubectl -n "$namespace" patch deployment "$deploy" --type=merge -p "$selector" || true
  done
fi

kubectl -n "$namespace" rollout status deployment --all --timeout="${IDYN_ROLLOUT_TIMEOUT:-420s}" || true
