# physical-moe-size10-20260521T112823Z

Status: completed

## Purpose
Physical size10 MoE Kubernetes run comparing default placement with iDynamics Policy 1 call-graph-aware placement.

## Cluster Mode
- Nodes: emu-worker-1, emu-worker-2, emu-worker-3, emu-worker-4, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9, k8s-emu-master
- Control-plane mode: included_by_node_pool_label_and_control_plane_toleration; taint_not_removed
- Live tc/qdisc impairments: none

## Key Metrics
| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Scheduler ready s | GDA build ms | Migrations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kubernetes default | 39.64 | 42.09 | 44.10 | 7.91 | 0 | 21.30 | 0.005 | 0 |
| iDynamics Policy 1 | 38.00 | 40.84 | 42.92 | 7.91 | 0 | 12.49 | 0.007 | 11 |

## Result
- Policy 1 p95 latency changed by 1.25 ms relative to Kubernetes default in this run.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

## Limitations
This is a physical size10 current-cluster run only. It does not support any 20/30/50-node physical claim.
