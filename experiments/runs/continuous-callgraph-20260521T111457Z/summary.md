# continuous-callgraph-20260521T111457Z

Status: completed

## Purpose
Evaluate continuous, overlapping Social Network workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `sinusoidal` with 48 snapshots at 5.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0353.
- Mean weighted edge distance: 0.0862.
- Mean hot-edge rank correlation: 0.9820.
- Latency/SLA-pressure correlation: 0.8704.

