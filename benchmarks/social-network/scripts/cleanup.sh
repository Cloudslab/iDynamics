#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-social-network}"
helm uninstall idyn-social --namespace "$namespace" >/dev/null 2>&1 || true
kubectl delete namespace "$namespace" --ignore-not-found=true
