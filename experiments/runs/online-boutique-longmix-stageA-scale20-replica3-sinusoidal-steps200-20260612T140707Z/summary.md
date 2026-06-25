# online-boutique-longmix-stageA-scale20-replica3-sinusoidal-steps200-20260612T140707Z

Status: completed

## Purpose
Evaluate continuous, overlapping `online-boutique` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `sinusoidal` with 200 snapshots at 1.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale20`.
- Replica profile: `replica3`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0117.
- Mean weighted edge distance: 0.0429.
- Mean hot-edge rank correlation: 0.9965.
- Mean request-mix entropy: 1.9566.
- Mean top-3 hotspot churn: 0.0126.
- Latency/SLA-pressure correlation: 0.9780.

