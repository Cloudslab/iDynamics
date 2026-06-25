# policy2-policy3-live-20260603T082241Z-scale10

Status: completed

## Purpose
Physical size10 MoE Kubernetes run comparing default placement with iDynamics Policy 1, Policy 2, Policy 3, and Policy 4.

## Cluster Mode
- Nodes: emu-worker-1, emu-worker-10, emu-worker-2, emu-worker-3, emu-worker-4, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9
- Control-plane mode: not_in_pool
- Live tc/qdisc impairments: none

## Key Metrics
| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Scheduler ready s | Objective cost | Migrations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kubernetes default | 59.29 | 64.27 | 73.02 | 7.92 | 0 | 3.03 | n/a | 0 |
| iDynamics Policy 1 | 53.63 | 57.95 | 62.96 | 7.92 | 0 | 4.36 | 8.000000 | 11 |
| iDynamics Policy 2 | 54.05 | 58.97 | 66.47 | 7.92 | 0 | 4.39 | 2.448500 | 9 |
| iDynamics Policy 3 | 58.51 | 62.55 | 64.42 | 7.92 | 0 | 5.40 | 0.000957 | 11 |
| iDynamics Policy 4 | 54.76 | 60.59 | 67.57 | 7.92 | 0 | 5.01 | 4.555059 | 11 |

## Result
- Policy 2 and Policy 3 used distinct placement groups and objective functions; raw pod placements and planner outputs are archived under `raw/` and `processed/`.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

