# online-boutique-longmix-stageB-scale45-replica5-linear-steps500-20260612T140711Z

Status: completed

## Purpose
Evaluate continuous, overlapping `online-boutique` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `linear` with 500 snapshots at 1.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Replica profile: `replica5`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0013.
- Mean weighted edge distance: 0.0391.
- Mean hot-edge rank correlation: 0.9991.
- Mean request-mix entropy: 1.9955.
- Mean top-3 hotspot churn: 0.0030.
- Latency/SLA-pressure correlation: 0.3204.

