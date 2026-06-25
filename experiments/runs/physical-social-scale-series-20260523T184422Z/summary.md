# physical-social-scale-series-20260523T184422Z

Status: completed

## Scope
Worker-only Social Network-compatible physical scale run comparing Kubernetes baseline and Policy 1 static placement.

Safe run setting: one repetition per scale/policy, 90 requests, concurrency 8, SLA threshold 150 ms.

## Results
| Scale | Policy | Success | p50 ms | p95 ms | p99 ms | Throughput rps | SLA viol. | Sched. ms | Ready ms | Pods | Nodes used |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scale5 | kubernetes | 90/90 | 21.15 | 79.20 | 82.43 | 223.50 | 0 | 0 | 6210 | 8 | 3 |
| scale5 | policy1 | 90/90 | 17.57 | 66.87 | 72.05 | 277.41 | 0 | 0 | 4896 | 8 | 1 |
| scale10 | kubernetes | 90/90 | 80.68 | 171.33 | 178.69 | 96.57 | 8 | 0 | 5291 | 8 | 4 |
| scale10 | policy1 | 90/90 | 29.41 | 77.79 | 81.18 | 206.17 | 0 | 0 | 4181 | 8 | 1 |
| scale20 | kubernetes | 90/90 | 76.88 | 168.24 | 172.94 | 107.56 | 9 | 0 | 5258 | 8 | 4 |
| scale20 | policy1 | 90/90 | 63.39 | 113.65 | 153.76 | 128.58 | 2 | 0 | 8720 | 8 | 1 |
| scale30 | kubernetes | 90/90 | 28.91 | 90.67 | 92.17 | 170.30 | 0 | 0 | 14895 | 8 | 3 |
| scale30 | policy1 | 90/90 | 67.60 | 114.81 | 159.64 | 120.56 | 3 | 0 | 9909 | 8 | 1 |
| scale45 | kubernetes | 90/90 | 73.43 | 111.41 | 114.50 | 122.97 | 1 | 0 | 7177 | 8 | 3 |
| scale45 | policy1 | 90/90 | 70.18 | 117.04 | 168.31 | 119.80 | 2 | 0 | 8783 | 8 | 1 |

## Resource Collection
Pod specs, pod placement, node capacities, events, and services are archived under `raw/` and `env/`. Observed CPU/memory utilization was requested through `kubectl top`, but the Metrics API was unavailable on this cluster; the stderr is archived in `env/metrics_api_top_nodes.txt.err`.

## Boundaries
This is a short smoke-scale physical run for reviewer-facing scale evidence. It is not a full DeathStarBench Social Network deployment and does not apply live tc impairment.
