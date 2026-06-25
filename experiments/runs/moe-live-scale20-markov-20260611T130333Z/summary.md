# moe-live-scale20-markov-20260611T130333Z

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
| Kubernetes default | 42.19 | 45.39 | 50.16 | 9.90 | 0 | 8.03 | 0.000 | n/a | 0 |
| CGA | 41.18 | 45.33 | 49.20 | 9.91 | 0 | 8.10 | 1.380 | 8.000000 | 10 |
| HDA | 42.48 | 46.16 | 48.88 | 9.90 | 0 | 6.18 | 3.013 | 4.555059 | 10 |
| Policy 2 | 41.65 | 44.62 | 47.90 | 9.90 | 0 | 8.77 | 2.257 | 2.448500 | 10 |
| Policy 3 | 44.93 | 47.63 | 50.42 | 9.91 | 0 | 6.40 | 1.823 | 0.000957 | 9 |

## Result
- CGA, HDA, Policy 2, and Policy 3 used distinct placement groups and objective functions; raw pod placements, load rows, hotspots, and planner outputs are archived under `raw/` and `processed/`.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

