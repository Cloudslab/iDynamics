#!/usr/bin/env bash
set -euo pipefail

namespace="${IDYN_NAMESPACE:-idyn-dsb-hotel}"
port="${IDYN_LOCAL_PORT:-15000}"
wrk2="${WRK2_BIN:-wrk}"
script="${DEATHSTAR_HOTEL_WRK_SCRIPT:-/home/ubuntu/idyn-external/deathstarbench/hotelReservation/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua}"

kubectl -n "$namespace" port-forward svc/frontend "$port:5000" --address 127.0.0.1 >/tmp/idyn-hotel-load-port-forward.log 2>&1 &
pf_pid=$!
trap 'kill "$pf_pid" >/dev/null 2>&1 || true' EXIT
sleep 3

"$wrk2" -t "${IDYN_THREADS:-2}" -c "${IDYN_CONNECTIONS:-16}" -d "${IDYN_DURATION:-30s}" -s "$script" "http://127.0.0.1:$port" ${IDYN_WRK_RATE:+-R "$IDYN_WRK_RATE"}
