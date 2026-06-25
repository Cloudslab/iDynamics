# moe-longmix-stageA-scale20-replica3-sinusoidal-steps200-20260612T141945Z

Status: completed

## Purpose
Evaluate continuous, overlapping `moe-serving` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `sinusoidal` with 200 snapshots at 0.10s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale20`.
- Replica profile: `replica3`.
- Policy comparison labels: `K8s default, CGA, HDA, Policy 2, Policy 3`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0127.
- Mean weighted edge distance: 0.0486.
- Mean hot-edge rank correlation: 0.9993.
- Mean request-mix entropy: 2.9680.
- Mean top-3 hotspot churn: 0.0050.
- Latency/SLA-pressure correlation: 0.8403.

