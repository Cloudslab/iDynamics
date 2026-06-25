# policy2-policy3-live-20260603T082825Z-scale20

Status: completed

## Purpose
Physical size20 MoE Kubernetes run comparing default placement with iDynamics Policy 1, Policy 2, Policy 3, and Policy 4.

## Cluster Mode
- Nodes: emu-worker-1, emu-worker-10, emu-worker-11, emu-worker-12, emu-worker-13, emu-worker-14, emu-worker-15, emu-worker-16, emu-worker-17, emu-worker-18, emu-worker-19, emu-worker-2, emu-worker-20, emu-worker-3, emu-worker-4, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9
- Control-plane mode: not_in_pool
- Live tc/qdisc impairments: none

## Key Metrics
| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Scheduler ready s | Objective cost | Migrations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kubernetes default | 58.48 | 62.92 | 76.53 | 7.93 | 0 | 4.88 | n/a | 0 |
| iDynamics Policy 1 | 53.54 | 56.66 | 59.84 | 7.93 | 0 | 4.73 | 8.000000 | 11 |
| iDynamics Policy 2 | 54.03 | 57.96 | 59.16 | 7.92 | 0 | 8.11 | 2.448500 | 9 |
| iDynamics Policy 3 | 56.90 | 60.46 | 62.54 | 7.92 | 0 | 5.27 | 0.000957 | 11 |
| iDynamics Policy 4 | 52.46 | 57.18 | 59.49 | 7.92 | 0 | 6.03 | 4.555059 | 10 |

## Result
- Policy 2 and Policy 3 used distinct placement groups and objective functions; raw pod placements and planner outputs are archived under `raw/` and `processed/`.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

## Limitations
This is a physical size20 current-cluster run only. It does not support any 20/30/50-node physical claim.
