#!/usr/bin/env bash
set -euo pipefail

kubectl delete namespace "${IDYN_NAMESPACE:-idyn-train-ticket}" --ignore-not-found=true
