# continuous-callgraph-20260521T111256Z

Status: completed

## Purpose
Evaluate continuous, overlapping Social Network workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `sinusoidal` with 48 snapshots at 5.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0000.
- Mean weighted edge distance: 0.0764.
- Mean hot-edge rank correlation: 0.9860.
- Latency/SLA-violation correlation: 0.0000.

## Limitations
The default run is synthetic/control-plane evidence for continuous call-graph evolution. It is not a physical cluster-scale performance result and makes no claim above 10 physical nodes.
