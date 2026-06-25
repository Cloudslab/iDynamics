#!/usr/bin/env bash
set -euo pipefail

kubectl_bin="${KUBECTL:-kubectl}"
expected_workers="${EXPECTED_WORKERS:-45}"
label_prefix="${LABEL_PREFIX:-idynamics.dev}"

usage() {
  cat <<USAGE
Usage: $0 [--expected-workers N]

Verifies deterministic nested worker-pool labels:
  ${label_prefix}/scale5=true, scale10=true, scale20=true, scale30=true, scale45=true
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
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

"$kubectl_bin" get nodes -o json | EXPECTED_WORKERS="$expected_workers" LABEL_PREFIX="$label_prefix" python3 -c '
import json
import os
import re
import sys

expected_workers = int(os.environ["EXPECTED_WORKERS"])
label_prefix = os.environ["LABEL_PREFIX"]
scales = (5, 10, 20, 30, 45)
data = json.load(sys.stdin)

def natural_key(value):
    return [int(part) if part.isdigit() else part for part in re.split(r"([0-9]+)", value)]

workers = []
control_planes = []
for item in data.get("items", []):
    name = item.get("metadata", {}).get("name", "")
    labels = item.get("metadata", {}).get("labels", {})
    if "node-role.kubernetes.io/control-plane" in labels or "node-role.kubernetes.io/master" in labels:
        control_planes.append((name, labels))
    else:
        workers.append((name, labels))

workers.sort(key=lambda item: natural_key(item[0]))
errors = []
if len(workers) != expected_workers:
    errors.append(f"expected {expected_workers} workers, found {len(workers)}")

for node, labels in control_planes:
    for scale in scales:
        key = f"{label_prefix}/scale{scale}"
        if labels.get(key) == "true":
            errors.append(f"control-plane node {node} has worker-pool label {key}=true")

for ordinal, (node, labels) in enumerate(workers, start=1):
    expected_index = str(ordinal)
    actual_index = labels.get(f"{label_prefix}/worker-index")
    if actual_index != expected_index:
        errors.append(f"{node}: expected worker-index {expected_index}, found {actual_index!r}")
    for scale in scales:
        key = f"{label_prefix}/scale{scale}"
        expected = ordinal <= scale
        actual = labels.get(key) == "true"
        if actual != expected:
            errors.append(f"{node}: expected {key}={str(expected).lower()}, found {labels.get(key)!r}")

for scale in scales:
    key = f"{label_prefix}/scale{scale}"
    members = [node for node, labels in workers if labels.get(key) == "true"]
    member_csv = ",".join(members)
    print(f"{key}=true count={len(members)} members={member_csv}")
    if len(members) != scale:
        errors.append(f"{key}=true expected {scale} members, found {len(members)}")

if errors:
    print("\nverification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print(f"verification passed for {expected_workers} workers and {len(control_planes)} control-plane nodes")
'
