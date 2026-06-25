#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-online-boutique}"
kubectl delete namespace "$namespace" --ignore-not-found=true
