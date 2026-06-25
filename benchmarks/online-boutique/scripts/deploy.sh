#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source_root="${ONLINE_BOUTIQUE_ROOT:-/home/ubuntu/idyn-external/online-boutique}"
namespace="${IDYN_NAMESPACE:-idyn-online-boutique}"
scale="${IDYN_SCALE:-scale10}"
replica_profile="${IDYN_REPLICA_PROFILE:-replica1}"
users="${IDYN_USERS:-10}"
rate="${IDYN_RATE:-5}"
manifest="${ONLINE_BOUTIQUE_MANIFEST:-$source_root/release/kubernetes-manifests.yaml}"

if [[ ! -f "$manifest" ]]; then
  echo "missing Online Boutique manifest: $manifest" >&2
  exit 2
fi

kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace "$namespace" istio-injection=enabled --overwrite
kubectl -n "$namespace" apply -f "$manifest"

selector="{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"idynamics.dev/$scale\":\"true\"}}}}}"
for deploy in adservice cartservice checkoutservice currencyservice emailservice frontend loadgenerator paymentservice productcatalogservice recommendationservice shippingservice redis-cart; do
  kubectl -n "$namespace" patch deployment "$deploy" --type=merge -p "$selector" || true
done

python3 - "$repo_root/benchmarks/online-boutique/adapter/replica_profiles.yaml" "$replica_profile" "$namespace" <<'PY'
import json
import subprocess
import sys

path, profile_name, namespace = sys.argv[1:4]
profile = json.loads(open(path, encoding="utf-8").read())["replica_profiles"][profile_name]
for service in profile.get("stateless_services", []):
    subprocess.run(["kubectl", "-n", namespace, "scale", "deployment", service, f"--replicas={profile['stateless_replicas']}"], check=True)
for service in profile.get("single_replica_services", []):
    subprocess.run(["kubectl", "-n", namespace, "scale", "deployment", service, "--replicas=1"], check=True)
for service in profile.get("client_services", []):
    subprocess.run(["kubectl", "-n", namespace, "scale", "deployment", service, "--replicas=1"], check=True)
PY

kubectl -n "$namespace" set env deployment/loadgenerator "USERS=$users" "RATE=$rate" FRONTEND_ADDR=frontend:80
kubectl -n "$namespace" rollout status deployment --all --timeout="${IDYN_ROLLOUT_TIMEOUT:-420s}"
