# continuous-longmix-scale45-markov-steps500-20260611T120735Z

Status: completed

## Purpose
Evaluate continuous, overlapping Social Network workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `markov` with 500 snapshots at 5.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay/model/control-plane`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0706.
- Mean weighted edge distance: 0.1562.
- Mean hot-edge rank correlation: 0.8285.
- Mean request-mix entropy: 1.0350.
- Mean top-3 hotspot churn: 0.1363.
- Latency/SLA-pressure correlation: 0.9001.

