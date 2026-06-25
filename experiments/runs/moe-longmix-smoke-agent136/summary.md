# moe-longmix-smoke-agent136

Status: completed

## Purpose
Evaluate continuous, overlapping `moe-serving` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `cache_stress` with 12 snapshots at 0.01s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale20`.
- Replica profile: `replica3`.
- Policy comparison labels: `K8s default, CGA, HDA, Policy 2, Policy 3`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0293.
- Mean weighted edge distance: 0.0909.
- Mean hot-edge rank correlation: 0.9931.
- Mean request-mix entropy: 2.2887.
- Mean top-3 hotspot churn: 0.0000.
- Latency/SLA-pressure correlation: 0.9727.

