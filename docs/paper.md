# Paper And Evidence Guide

[Documentation index](index.md) | [Reproducibility](reproducibility.md) | [Architecture](architecture.md)

This page maps paper-facing terminology to repository components and artifact
boundaries. It is a guide to the public repository, not a copy of the manuscript
text.

## Component Names

| Paper-facing name | Repository implementation |
| --- | --- |
| Graph Dynamics Analyzer (GDA) | `idynamics.gda` and `iDynamicsPackagesModules.GraphDynamicsAnalyzer` compatibility modules. |
| Network Dynamics Manager (NDM) | `idynamics.network.traces` plus legacy network emulation and measurement helpers. |
| Scheduling Policy Extender (SPE) | `idynamics.policies`, `scripts/policies/run_policy.py`, and legacy SPE compatibility modules. |
| CGA | Call-graph-aware planner represented by `Policy1TrafficAffinity`. |
| HDA | Hybrid-dynamics-aware planner represented by `Policy4HybridDynamics`. |
| Trace providers | `SyntheticDistanceRandomProvider`, `BurstCorrelatedProvider`, and `CsvMatrixReplayProvider`. |
| Run ledgers | `experiments/runs/<run-id>` created by `idynamics.ledger.run`. |
| Evidence types | Live physical, replay, synthetic control-plane, compatibility, and CPU-only MoE evidence. |

## Artifact Map

The authoritative artifact index is
[`../reproducibility/manifest.yaml`](../reproducibility/manifest.yaml). Each item
folder has its own `manifest.yaml`, committed `data/`, deterministic
`expected/`, and `run.sh`.

| Item | Folder | Evidence class | Boundary summary |
| --- | --- | --- | --- |
| Table I | [`table-i-capability-comparison`](../reproducibility/items/table-i-capability-comparison) | Literature and feature-scope | Not an empirical performance result. |
| Table II | [`table-ii-istio-mesh-overhead`](../reproducibility/items/table-ii-istio-mesh-overhead) | Live physical | Controlled Fortio sidecar comparison at named placement-pool scales. |
| Table III | [`table-iii-gda-overhead`](../reproducibility/items/table-iii-gda-overhead) | Live physical plus synthetic control-plane | Real rows include Prometheus query latency; synthetic rows isolate local graph construction. |
| Table IV | [`table-iv-ndm-accuracy`](../reproducibility/items/table-iv-ndm-accuracy) | Live physical validation with legacy support data | Directed-pair delay and saturated-bandwidth validation for the named testbed shape. |
| Table V | [`table-v-network-trace-provider`](../reproducibility/items/table-v-network-trace-provider) | Synthetic and replay trace statistics | Matrix statistics only, not application latency or scheduler quality. |
| Table VI | [`table-vi-ripe-calibration`](../reproducibility/items/table-vi-ripe-calibration) | External latency calibration | Latency-scale fit for one public RTT sample window; no bandwidth calibration claim. |
| Table VII | [`table-vii-request-mix-modes`](../reproducibility/items/table-vii-request-mix-modes) | Workload-mode definition | Defines request-mix semantics; not a performance table. |
| Table VIII | [`table-viii-continuous-robustness`](../reproducibility/items/table-viii-continuous-robustness) | Replay and control-plane | Same-snapshot policy outputs over generated call-graph traces, not live application latency. |
| Figure 7 | [`figure-07-ripe-cdf`](../reproducibility/items/figure-07-ripe-cdf) | External latency calibration | Visualizes RTT CDF fit only. |
| Figure 8 | [`figure-08-continuous-longmix`](../reproducibility/items/figure-08-continuous-longmix) | Replay and control-plane | Continuous Social Network trace visualization; response-time curves are replay/model outputs. |
| Figure 9 | [`figure-09-application-generality`](../reproducibility/items/figure-09-application-generality) | Replay plus CPU-only MoE | Common adapter schema across Online Boutique and CPU-only MoE-style benchmark. |

## Evidence Boundaries

Use these labels consistently:

- Live physical evidence means a named testbed, workload, telemetry collection,
  or traffic-control validation actually ran.
- Replay evidence means committed traces or generated traces were replayed into
  deterministic scripts.
- Synthetic control-plane evidence covers local graph construction, query-count
  scaling, trace generation, and policy planning without end-to-end application
  latency claims.
- Compatibility evidence covers adapter packaging, deploy/smoke/load/collect
  plumbing, and cluster readiness checks.
- CPU-only MoE evidence covers the repository-local MoE-style service graph and
  CPU work model only.

## Citation

Use the citation from the root [`README.md`](../README.md#citation) when citing
the paper. Preserve the artifact claim boundaries above when citing generated
tables or figures.
