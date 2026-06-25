#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
image="${MOE_IMAGE:-moe-serving:latest}"
builder="${IDYN_CONTAINER_BUILDER:-}"

if [[ -z "$builder" ]]; then
  if command -v docker >/dev/null 2>&1; then
    builder="docker"
  elif command -v podman >/dev/null 2>&1; then
    builder="podman"
  else
    echo "docker or podman is required; set IDYN_CONTAINER_BUILDER to override" >&2
    exit 2
  fi
fi

"$builder" build -t "$image" "$repo_root/examples/moe-serving"

if [[ "${IDYN_PUSH_IMAGE:-0}" == "1" ]]; then
  "$builder" push "$image"
fi

printf '%s\n' "$image"
