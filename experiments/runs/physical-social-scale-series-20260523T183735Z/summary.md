# physical-social-scale-series-20260523T183735Z

Status: superseded

This run completed, but it is superseded by `physical-social-scale-series-20260523T184422Z` because the inherited load generator wrote generic `raw/kubernetes_loadgen.csv` and `raw/policy1_loadgen.csv` names that were overwritten across scales. The processed metrics remain useful for engineering comparison, but paper claims must use the replacement ledger with per-scale raw load CSVs.

## Scope
Worker-only Social Network-compatible physical scale run comparing Kubernetes baseline and Policy 1 static placement.

Safe run setting: one repetition per scale/policy, 90 requests, concurrency 8, SLA threshold 150 ms.

## Results
| Scale | Policy | Success | p50 ms | p95 ms | p99 ms | Throughput rps | SLA viol. | Sched. ms | Ready ms | Pods | Nodes used |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scale5 | kubernetes | 90/90 | 33.36 | 95.96 | 99.83 | 152.84 | 0 | 0 | 11533 | 8 | 3 |
| scale5 | policy1 | 90/90 | 36.77 | 85.96 | 96.11 | 188.35 | 0 | 0 | 6130 | 8 | 1 |
| scale10 | kubernetes | 90/90 | 21.17 | 80.29 | 83.60 | 197.63 | 0 | 0 | 11415 | 8 | 4 |
| scale10 | policy1 | 90/90 | 40.26 | 93.04 | 95.68 | 175.92 | 0 | 0 | 7386 | 8 | 1 |
| scale20 | kubernetes | 90/90 | 66.80 | 119.17 | 159.43 | 120.67 | 4 | 0 | 9618 | 8 | 4 |
| scale20 | policy1 | 90/90 | 72.62 | 123.63 | 163.66 | 106.74 | 3 | 0 | 10180 | 8 | 1 |
| scale30 | kubernetes | 90/90 | 41.68 | 94.03 | 94.67 | 167.22 | 0 | 0 | 10406 | 8 | 5 |
| scale30 | policy1 | 90/90 | 74.29 | 161.07 | 172.18 | 103.89 | 5 | 0 | 8884 | 8 | 1 |
| scale45 | kubernetes | 90/90 | 74.04 | 1047.19 | 1051.90 | 52.90 | 9 | 0 | 9920 | 8 | 5 |
| scale45 | policy1 | 90/90 | 59.79 | 113.48 | 117.52 | 130.80 | 1 | 0 | 8396 | 8 | 1 |

## Resource Collection
Pod specs, pod placement, node capacities, events, and services are archived under `raw/` and `env/`. Observed CPU/memory utilization was requested through `kubectl top`, but the Metrics API was unavailable on this cluster; the stderr is archived in `env/metrics_api_top_nodes.txt.err`.

## Boundaries
This is a short smoke-scale physical run for reviewer-facing scale evidence. It is not a full DeathStarBench Social Network deployment and does not apply live tc impairment.
