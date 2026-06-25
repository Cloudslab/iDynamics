# continuous-longmix-scale45-linear-steps200-20260611T120729Z

Status: completed

## Purpose
Evaluate continuous, overlapping Social Network workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `linear` with 200 snapshots at 5.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay/model/control-plane`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0003.
- Mean weighted edge distance: 0.0398.
- Mean hot-edge rank correlation: 0.9991.
- Mean request-mix entropy: 1.4883.
- Mean top-3 hotspot churn: 0.0101.
- Latency/SLA-pressure correlation: 0.9786.

## Limitations
The default run is synthetic/control-plane evidence for continuous call-graph evolution. Policy latency/SLA outputs are replay/model/control-plane evidence. The run is not a physical cluster-scale performance result unless live workload logs are present in this ledger.
