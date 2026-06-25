# continuous-longmix-scale45-linear-steps1000-20260611T120743Z

Status: completed

## Purpose
Evaluate continuous, overlapping Social Network workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `linear` with 1000 snapshots at 5.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay/model/control-plane`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0005.
- Mean weighted edge distance: 0.0413.
- Mean hot-edge rank correlation: 0.9998.
- Mean request-mix entropy: 1.4892.
- Mean top-3 hotspot churn: 0.0020.
- Latency/SLA-pressure correlation: 0.9794.

