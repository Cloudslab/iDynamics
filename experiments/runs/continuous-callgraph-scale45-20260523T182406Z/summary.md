# continuous-callgraph-scale45-20260523T182406Z

Status: completed

## Purpose
Evaluate continuous, overlapping Social Network workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `markov` with 36 snapshots at 2.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45-control-plane`.
- Policy comparison labels: `kubernetes, policy1, policy4`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0076.
- Mean weighted edge distance: 0.2591.
- Mean hot-edge rank correlation: 0.7345.
- Latency/SLA-pressure correlation: 0.9323.

## Limitations
The default run is synthetic/control-plane evidence for continuous call-graph evolution. It is not a physical cluster-scale performance result unless live workload logs are present in this ledger.
