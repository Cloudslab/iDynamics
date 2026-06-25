#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-social-network}"
scale="${IDYN_SCALE:-scale45}"
chart="${DEATHSTAR_SOCIAL_CHART:-/home/ubuntu/idyn-external/deathstarbench/socialNetwork/helm-chart/socialnetwork}"

kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$namespace" istio-injection=enabled --overwrite
helm dependency build "$chart" >/tmp/idyn-social-network-helm-dependency.log 2>&1 || true
helm upgrade --install idyn-social "$chart" \
  --namespace "$namespace" \
  --create-namespace \
  --timeout "${IDYN_DEPLOY_TIMEOUT:-480s}" \
  --set global.replicas=1 \
  --set global.hpa.enabled=false \
  --set-string global.imagePullPolicy=IfNotPresent

selector="{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"idynamics.dev/$scale\":\"true\"}}}}}"
for deploy in $(kubectl -n "$namespace" get deploy -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'); do
  kubectl -n "$namespace" patch deployment "$deploy" --type=merge -p "$selector" || true
done

kubectl -n "$namespace" wait --for=condition=available deployment --all --timeout="${IDYN_ROLLOUT_TIMEOUT:-600s}"
