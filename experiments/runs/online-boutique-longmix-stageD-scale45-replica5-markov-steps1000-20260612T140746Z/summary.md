# online-boutique-longmix-stageD-scale45-replica5-markov-steps1000-20260612T140746Z

Status: completed

## Purpose
Evaluate continuous, overlapping `online-boutique` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `markov` with 1000 snapshots at 1.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Replica profile: `replica5`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0463.
- Mean weighted edge distance: 0.1727.
- Mean hot-edge rank correlation: 0.7608.
- Mean request-mix entropy: 1.4076.
- Mean top-3 hotspot churn: 0.1681.
- Latency/SLA-pressure correlation: 0.7100.

