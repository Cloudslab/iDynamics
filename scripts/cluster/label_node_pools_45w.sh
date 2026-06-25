#!/usr/bin/env bash
set -euo pipefail

kubectl_bin="${KUBECTL:-kubectl}"
expected_workers="${EXPECTED_WORKERS:-45}"
label_prefix="${LABEL_PREFIX:-idynamics.dev}"
apply="true"

usage() {
  cat <<USAGE
Usage: $0 [--dry-run] [--expected-workers N]

Labels deterministic nested worker pools for physical-scale experiments.
Workers are selected by excluding control-plane/master role labels and are
ordered by natural node name sort.

Labels:
  ${label_prefix}/worker-index=<1..N>
  ${label_prefix}/scale5=true    on workers 1..5
  ${label_prefix}/scale10=true   on workers 1..10
  ${label_prefix}/scale20=true   on workers 1..20
  ${label_prefix}/scale30=true   on workers 1..30
  ${label_prefix}/scale45=true   on workers 1..45
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      apply="false"
      shift
      ;;
    --expected-workers)
      expected_workers="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v "$kubectl_bin" >/dev/null 2>&1; then
  echo "kubectl command not found: $kubectl_bin" >&2
  exit 127
fi

mapfile -t workers < <("$kubectl_bin" get nodes -o json | python3 -c '
import json
import re
import sys

data = json.load(sys.stdin)

def natural_key(value):
    return [int(part) if part.isdigit() else part for part in re.split(r"([0-9]+)", value)]

workers = []
for item in data.get("items", []):
    labels = item.get("metadata", {}).get("labels", {})
    if "node-role.kubernetes.io/control-plane" in labels:
        continue
    if "node-role.kubernetes.io/master" in labels:
        continue
    workers.append(item.get("metadata", {}).get("name", ""))

for name in sorted(filter(None, workers), key=natural_key):
    print(name)
'
)

if [ "${#workers[@]}" -ne "$expected_workers" ]; then
  echo "expected ${expected_workers} workers, found ${#workers[@]}" >&2
  printf 'workers found:\n' >&2
  printf '  %s\n' "${workers[@]}" >&2
  exit 1
fi

scales=(5 10 20 30 45)
for scale in "${scales[@]}"; do
  if [ "$scale" -gt "$expected_workers" ]; then
    echo "scale${scale} exceeds worker count ${expected_workers}" >&2
    exit 1
  fi
done

echo "worker order:"
printf '  %s\n' "${workers[@]}"

if [ "$apply" != "true" ]; then
  echo "dry run only; no labels were changed"
  exit 0
fi

for node in "${workers[@]}"; do
  "$kubectl_bin" label node "$node" \
    "${label_prefix}/worker-index-" \
    "${label_prefix}/scale5-" \
    "${label_prefix}/scale10-" \
    "${label_prefix}/scale20-" \
    "${label_prefix}/scale30-" \
    "${label_prefix}/scale45-" \
    >/dev/null 2>&1 || true
done

for i in "${!workers[@]}"; do
  node="${workers[$i]}"
  ordinal="$((i + 1))"
  "$kubectl_bin" label node "$node" "${label_prefix}/worker-index=${ordinal}" --overwrite >/dev/null
  for scale in "${scales[@]}"; do
    if [ "$ordinal" -le "$scale" ]; then
      "$kubectl_bin" label node "$node" "${label_prefix}/scale${scale}=true" --overwrite >/dev/null
    fi
  done
done

echo "applied nested ${label_prefix}/scale{5,10,20,30,45} labels to ${expected_workers} workers"
