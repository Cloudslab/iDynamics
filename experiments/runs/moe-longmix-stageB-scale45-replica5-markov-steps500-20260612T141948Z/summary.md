# moe-longmix-stageB-scale45-replica5-markov-steps500-20260612T141948Z

Status: completed

## Purpose
Evaluate continuous, overlapping `moe-serving` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `markov` with 500 snapshots at 0.10s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Replica profile: `replica5`.
- Policy comparison labels: `K8s default, CGA, HDA, Policy 2, Policy 3`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0470.
- Mean weighted edge distance: 0.1249.
- Mean hot-edge rank correlation: 0.9357.
- Mean request-mix entropy: 1.8278.
- Mean top-3 hotspot churn: 0.0998.
- Latency/SLA-pressure correlation: 0.6259.

