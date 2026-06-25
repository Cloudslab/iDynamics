# moe-live-scale10-phase-shift-20260611T124429Z

Status: completed

## Purpose
Physical scale10 MoE Kubernetes run comparing K8s default, CGA, HDA, Policy 2 critical-path latency, and Policy 3 bandwidth/payload-aware placement.

## Cluster Mode
- Nodes: emu-worker-1, emu-worker-10, emu-worker-2, emu-worker-3, emu-worker-4, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9
- Control-plane mode: not_in_pool
- Live tc/qdisc impairments: none

## Key Metrics
| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Ready s | Decision ms | Objective cost | Migrations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kubernetes default | 44.02 | 46.86 | 48.46 | 9.91 | 0 | 5.23 | 0.000 | n/a | 0 |
| CGA | 40.46 | 43.92 | 45.64 | 9.91 | 0 | 8.46 | 0.827 | 8.000000 | 10 |
| HDA | 41.49 | 44.81 | 49.16 | 9.91 | 0 | 9.07 | 1.742 | 4.555059 | 10 |
| Policy 2 | 42.84 | 46.77 | 52.84 | 9.91 | 0 | 4.30 | 1.192 | 2.448500 | 10 |
| Policy 3 | 44.93 | 48.76 | 50.74 | 9.91 | 0 | 6.48 | 1.410 | 0.000957 | 8 |

## Result
- CGA, HDA, Policy 2, and Policy 3 used distinct placement groups and objective functions; raw pod placements, load rows, hotspots, and planner outputs are archived under `raw/` and `processed/`.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

## Limitations
This is a physical scale10 current-cluster CPU-only microservice run only. It does not support GPU-aware production LLM-serving claims.
