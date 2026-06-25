# online-boutique-longmix-stageB-scale45-replica5-step-steps500-20260612T140710Z

Status: completed

## Purpose
Evaluate continuous, overlapping `online-boutique` workload mixes and fixed-interval call-graph snapshots.

## Result
- Implemented and exercised `WorkloadMixer` mode `step` with 500 snapshots at 1.00s intervals.
- Archived request probabilities, per-snapshot edge weights, graph-distance metrics, latency/SLA signals, and an aligned SVG timeline.
- Evidence scope label: `scale45`.
- Replica profile: `replica5`.
- Policy comparison labels: `K8s default, CGA, HDA`.
- Policy latency/SLA evidence type: `replay`.
- Live wrk execution: `False`.

## Key Metrics
- Mean edge Jaccard distance: 0.0036.
- Mean weighted edge distance: 0.0445.
- Mean hot-edge rank correlation: 0.9926.
- Mean request-mix entropy: 1.2535.
- Mean top-3 hotspot churn: 0.0062.
- Latency/SLA-pressure correlation: 0.5338.

## Limitations
The default run is replay evidence for continuous call-graph evolution. Policy latency/SLA outputs are replay evidence. The run is not a live physical cluster-scale performance result unless live workload logs are present in this ledger, and it does not support saturated 45-worker scaling claims without recorded pod/node occupancy.
