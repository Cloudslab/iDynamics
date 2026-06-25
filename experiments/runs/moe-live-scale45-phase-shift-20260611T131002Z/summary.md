# moe-live-scale45-phase-shift-20260611T131002Z

Status: completed

## Purpose
Physical scale45 MoE Kubernetes run comparing K8s default, CGA, HDA, Policy 2 critical-path latency, and Policy 3 bandwidth/payload-aware placement.

## Cluster Mode
- Nodes: emu-worker-1, emu-worker-10, emu-worker-11, emu-worker-12, emu-worker-13, emu-worker-14, emu-worker-15, emu-worker-16, emu-worker-17, emu-worker-18, emu-worker-19, emu-worker-2, emu-worker-20, emu-worker-21, emu-worker-22, emu-worker-23, emu-worker-24, emu-worker-25, emu-worker-26, emu-worker-27, emu-worker-28, emu-worker-29, emu-worker-3, emu-worker-30, emu-worker-31, emu-worker-32, emu-worker-33, emu-worker-34, emu-worker-35, emu-worker-36, emu-worker-37, emu-worker-38, emu-worker-39, emu-worker-4, emu-worker-40, emu-worker-41, emu-worker-42, emu-worker-43, emu-worker-44, emu-worker-45, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9
- Control-plane mode: not_in_pool
- Live tc/qdisc impairments: none

## Key Metrics
| Policy | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | Ready s | Decision ms | Objective cost | Migrations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kubernetes default | 42.13 | 45.74 | 53.80 | 9.91 | 0 | 7.81 | 0.000 | n/a | 0 |
| CGA | 42.15 | 46.41 | 50.73 | 9.91 | 0 | 5.20 | 4.073 | 8.000000 | 10 |
| HDA | 41.81 | 45.04 | 45.92 | 9.92 | 0 | 7.04 | 6.347 | 4.555059 | 10 |
| Policy 2 | 42.65 | 46.89 | 53.42 | 9.91 | 0 | 6.94 | 5.035 | 2.448500 | 10 |
| Policy 3 | 41.73 | 44.86 | 48.39 | 9.91 | 0 | 8.10 | 5.019 | 0.000957 | 10 |

## Result
- CGA, HDA, Policy 2, and Policy 3 used distinct placement groups and objective functions; raw pod placements, load rows, hotspots, and planner outputs are archived under `raw/` and `processed/`.
- Network target-vs-measured error is not applicable because this run did not apply live network impairment.

