#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-moe-serving}"
kubectl delete namespace "$namespace" --ignore-not-found=true
