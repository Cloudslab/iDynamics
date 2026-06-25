#!/usr/bin/env bash
set -euo pipefail

kubectl delete namespace "${IDYN_NAMESPACE:-idyn-sock-shop}" --ignore-not-found=true
