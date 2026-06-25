#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export RUN_ID="${RUN_ID:-continuous-longmix-scale45-markov-steps500-20260611T120735Z}"
export CONTINUOUS_CALLGRAPH_MODE="markov"
export CONTINUOUS_CALLGRAPH_STEPS="500"
export CONTINUOUS_CALLGRAPH_INTERVAL_S="5"
export CONTINUOUS_CALLGRAPH_TOTAL_QPS="90"
export CONTINUOUS_CALLGRAPH_SEED="31"
export CONTINUOUS_CALLGRAPH_LIVE_WRK="0"
export CONTINUOUS_CALLGRAPH_TRACE_CSV=""
export CONTINUOUS_CALLGRAPH_SCALE="scale45"
export CONTINUOUS_CALLGRAPH_POLICIES="kubernetes-default,cga,hda"
export CONTINUOUS_CALLGRAPH_BASE_URL="http://nginx-thrift.social-network.svc.cluster.local:8080"
export CONTINUOUS_CALLGRAPH_WRK_BIN="/home/ubuntu/DeathStarBench/wrk2/wrk"

"$repo_root/scripts/experiments/run_continuous_callgraph.sh"
