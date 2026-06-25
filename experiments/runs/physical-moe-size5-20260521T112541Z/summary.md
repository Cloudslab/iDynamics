# physical-moe-size5-20260521T112541Z

Status: completed

## Purpose
Physical size5 MoE Kubernetes run comparing default placement with iDynamics Policy 1 call-graph-aware placement.

## Cluster Mode
- Nodes: emu-worker-1, emu-worker-2, emu-worker-3, emu-worker-4, emu-worker-5
- Control-plane mode: not_in_pool
- Live tc/qdisc impairments: none

## Key Metrics
| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Scheduler ready s | GDA build ms | Migrations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kubernetes default | 41.01 | 43.65 | 45.66 | 7.91 | 0 | 17.67 | 0.010 | 0 |
| iDynamics Policy 1 | 39.01 | 41.75 | 44.26 | 7.91 | 0 | 8.51 | 0.006 | 9 |

## Result
- Policy 1 p95 latency changed by 1.90 ms relative to Kubernetes default in this run.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

