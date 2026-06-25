# moe-sidecar-s5-20260523T171503Z

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
| Kubernetes default | 48.49 | 60.28 | 97.35 | 18.24 | 0 | 24.79 | 0.030 | 0 |
| iDynamics Policy 1 | 45.53 | 55.47 | 94.79 | 18.32 | 0 | 7.38 | 0.007 | 7 |

## Result
- Policy 1 p95 latency changed by 4.80 ms relative to Kubernetes default in this run.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

## Limitations
This is a physical size5 current-cluster run only. It does not support any 20/30/50-node physical claim.
