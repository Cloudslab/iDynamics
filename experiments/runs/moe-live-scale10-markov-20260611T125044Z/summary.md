# moe-live-scale10-markov-20260611T125044Z

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
| Kubernetes default | 42.87 | 46.13 | 56.80 | 9.90 | 0 | 6.67 | 0.000 | n/a | 0 |
| CGA | 40.97 | 43.83 | 57.13 | 9.90 | 0 | 6.75 | 1.004 | 8.000000 | 10 |
| HDA | 42.49 | 45.95 | 51.74 | 9.90 | 0 | 9.09 | 2.102 | 4.555059 | 11 |
| Policy 2 | 41.93 | 45.30 | 55.59 | 9.90 | 0 | 10.28 | 1.368 | 2.448500 | 11 |
| Policy 3 | 43.02 | 46.67 | 50.77 | 9.91 | 0 | 9.15 | 1.397 | 0.000957 | 11 |

## Result
- CGA, HDA, Policy 2, and Policy 3 used distinct placement groups and objective functions; raw pod placements, load rows, hotspots, and planner outputs are archived under `raw/` and `processed/`.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

## Limitations
This is a physical scale10 current-cluster CPU-only microservice run only. It does not support GPU-aware production LLM-serving claims.
