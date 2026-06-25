#!/usr/bin/env bash
set -euo pipefail

idyn_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

idyn_timestamp() {
  date -u +%Y%m%dT%H%M%SZ
}

idyn_init_run_ledger() {
  if [ "$#" -lt 1 ]; then
    echo "usage: idyn_init_run_ledger RUN_ID [CONFIG_FILE]" >&2
    return 2
  fi

  local run_id="$1"
  local config_file="${2:-}"
  local repo_root
  repo_root="$(idyn_repo_root)"
  local run_dir="${repo_root}/experiments/runs/${run_id}"

  mkdir -p \
    "${run_dir}/env" \
    "${run_dir}/raw" \
    "${run_dir}/processed" \
    "${run_dir}/figures" \
    "${run_dir}/logs"

  if [ -n "$config_file" ] && [ -f "$config_file" ]; then
    cp "$config_file" "${run_dir}/config.yaml"
  elif [ ! -f "${run_dir}/config.yaml" ]; then
    cat >"${run_dir}/config.yaml" <<YAML
run_id: ${run_id}
created_utc: $(idyn_timestamp)
purpose: TBD
physical_scale_claim: none
YAML
  fi

  git -C "$repo_root" rev-parse HEAD >"${run_dir}/git_sha.txt" 2>/dev/null || echo "no-git-sha" >"${run_dir}/git_sha.txt"
  git -C "$repo_root" status --short --branch >"${run_dir}/git_status.txt" 2>/dev/null || true
  printf '%s\n' "${CODEX_MODEL:-codex-cli-local}" >"${run_dir}/codex_model.txt"
  : >"${run_dir}/commands.log"

  if [ ! -f "${run_dir}/summary.md" ]; then
    cat >"${run_dir}/summary.md" <<MD
# ${run_id}

Status: initialized

## Purpose
TBD

## Result
TBD

## Limitations
TBD
MD
  fi


  printf '%s\n' "$run_dir"
}

idyn_log_command() {
  if [ "$#" -lt 2 ]; then
    echo "usage: idyn_log_command RUN_DIR COMMAND..." >&2
    return 2
  fi

  local run_dir="$1"
  shift
  printf '[%s] %s\n' "$(idyn_timestamp)" "$*" >>"${run_dir}/commands.log"
}
