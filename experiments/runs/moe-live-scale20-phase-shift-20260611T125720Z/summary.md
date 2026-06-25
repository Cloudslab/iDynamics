# moe-live-scale20-phase-shift-20260611T125720Z

Status: completed

## Purpose
Physical scale20 MoE Kubernetes run comparing K8s default, CGA, HDA, Policy 2 critical-path latency, and Policy 3 bandwidth/payload-aware placement.

## Cluster Mode
- Nodes: emu-worker-1, emu-worker-10, emu-worker-11, emu-worker-12, emu-worker-13, emu-worker-14, emu-worker-15, emu-worker-16, emu-worker-17, emu-worker-18, emu-worker-19, emu-worker-2, emu-worker-20, emu-worker-3, emu-worker-4, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9
- Control-plane mode: not_in_pool
- Live tc/qdisc impairments: none

## Key Metrics
| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Ready s | Decision ms | Objective cost | Migrations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kubernetes default | 43.23 | 46.26 | 48.16 | 9.91 | 0 | 5.19 | 0.000 | n/a | 0 |
| CGA | 40.84 | 43.45 | 51.90 | 9.91 | 0 | 6.35 | 1.447 | 8.000000 | 10 |
| HDA | 41.72 | 44.28 | 50.55 | 9.91 | 0 | 8.80 | 3.435 | 4.555059 | 11 |
| Policy 2 | 41.98 | 46.48 | 52.59 | 9.91 | 0 | 3.26 | 2.130 | 2.448500 | 11 |
| Policy 3 | 43.43 | 47.26 | 52.96 | 9.91 | 0 | 4.31 | 1.946 | 0.000957 | 11 |

## Result
- CGA, HDA, Policy 2, and Policy 3 used distinct placement groups and objective functions; raw pod placements, load rows, hotspots, and planner outputs are archived under `raw/` and `processed/`.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

## Limitations
This is a physical scale20 current-cluster CPU-only microservice run only. It does not support GPU-aware production LLM-serving claims.
