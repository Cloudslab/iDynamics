#!/usr/bin/env bash
set -euo pipefail

kubectl delete namespace "${IDYN_NAMESPACE:-idyn-dsb-hotel}" --ignore-not-found=true
