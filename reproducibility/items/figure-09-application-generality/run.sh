#!/usr/bin/env bash
set -euo pipefail
artifact_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$artifact_dir/scripts/generate.py" "$@"
