# continuous-longmix-scale45-sinusoidal-steps200-20260611T120729Z

Status: completed

## Purpose
Evaluate continuous, overlapping Social Network workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `sinusoidal` with 200 snapshots at 5.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay/model/control-plane`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0155.
- Mean weighted edge distance: 0.0464.
- Mean hot-edge rank correlation: 0.9960.
- Mean request-mix entropy: 1.3865.
- Mean top-3 hotspot churn: 0.0226.
- Latency/SLA-pressure correlation: 0.9008.

