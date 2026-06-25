# moe-longmix-stageD-scale45-replica5-markov-steps1000-20260612T141958Z

Status: completed

## Purpose
Evaluate continuous, overlapping `moe-serving` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `markov` with 1000 snapshots at 0.10s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Replica profile: `replica5`.
- Policy comparison labels: `K8s default, CGA, HDA, Policy 2, Policy 3`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0542.
- Mean weighted edge distance: 0.1253.
- Mean hot-edge rank correlation: 0.9376.
- Mean request-mix entropy: 1.8278.
- Mean top-3 hotspot churn: 0.1020.
- Latency/SLA-pressure correlation: 0.5968.

