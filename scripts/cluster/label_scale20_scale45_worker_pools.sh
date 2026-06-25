#!/usr/bin/env bash
set -euo pipefail

kubectl_bin="${KUBECTL:-kubectl}"
expected_workers="${EXPECTED_WORKERS:-45}"
label_prefix="${LABEL_PREFIX:-idynamics.dev}"
apply="true"
output_json=""

usage() {
  cat <<USAGE
Usage: $0 [--dry-run] [--expected-workers N] [--output-json PATH]

Labels deterministic nested scale20 and scale45 worker pools. Workers are
selected by excluding control-plane/master role labels and sorting node names.

Labels:
  ${label_prefix}/worker-index=<1..N>
  ${label_prefix}/scale20=true on workers 1..20
  ${label_prefix}/scale45=true on workers 1..45
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
    --output-json)
      output_json="$2"
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
')

if [ "${#workers[@]}" -lt "$expected_workers" ]; then
  echo "expected at least ${expected_workers} workers, found ${#workers[@]}" >&2
  exit 1
fi

if [ "$expected_workers" -lt 45 ]; then
  echo "scale45 requires expected-workers >= 45" >&2
  exit 1
fi

echo "scale20 workers:"
printf '  %s\n' "${workers[@]:0:20}"
echo "scale45 workers:"
printf '  %s\n' "${workers[@]:0:45}"

if [ -n "$output_json" ]; then
  OUTPUT_JSON="$output_json" python3 - "${workers[@]}" <<'PY'
import json
import os
import sys
workers = sys.argv[1:]
payload = {
    "scale20": workers[:20],
    "scale45": workers[:45],
}
with open(os.environ["OUTPUT_JSON"], "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
    fh.write("\n")
PY
fi

if [ "$apply" != "true" ]; then
  echo "dry run only; no labels were changed"
  exit 0
fi

for node in "${workers[@]}"; do
  "$kubectl_bin" label node "$node" \
    "${label_prefix}/worker-index-" \
    "${label_prefix}/scale20-" \
    "${label_prefix}/scale45-" \
    >/dev/null 2>&1 || true
done

for i in "${!workers[@]}"; do
  node="${workers[$i]}"
  ordinal="$((i + 1))"
  "$kubectl_bin" label node "$node" "${label_prefix}/worker-index=${ordinal}" --overwrite >/dev/null
  if [ "$ordinal" -le 20 ]; then
    "$kubectl_bin" label node "$node" "${label_prefix}/scale20=true" --overwrite >/dev/null
  fi
  if [ "$ordinal" -le 45 ]; then
    "$kubectl_bin" label node "$node" "${label_prefix}/scale45=true" --overwrite >/dev/null
  fi
done

echo "applied ${label_prefix}/scale20 and ${label_prefix}/scale45 labels"
