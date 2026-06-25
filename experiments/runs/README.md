# Cleaned Run Artifacts

This directory contains 106 cleaned experiment run folders. The folders are
kept as lightweight references for readers of `IEEE_TSC_iDynamics_Revision.pdf`.

Only runs whose run-level `summary.md` status is `completed`, `performance
evidence`, or `measured` are kept in this cleaned copy.

## What Was Kept

Common useful files:

- `summary.md`: run-level purpose, status, result, and key metrics when present.
- `config.yaml`: parameters, scale, workload, policy, and evidence labels.
- `raw/`: manifests, traces, load-generator CSVs, or captured cluster state.
- `processed/`: metrics, summaries, and table-ready CSV/JSON outputs.
- `env/`: environment snapshots when they help interpret the run.

## What Was Removed

The cleaned copy removes files that are not useful for paper readers:

- `paper_claims.md`
- local tool metadata files
- `git_sha.txt`
- `git_status.txt`
- `commands.log`
- `logs/`
- `figures/`
- run folders whose run-level `summary.md` status was not `completed`,
  `performance evidence`, or `measured`

The full uncleaned ledgers are preserved separately outside this repository.

## Run Families

| Family | Count | Typical purpose |
| --- | ---: | --- |
| MoE long-mix replay | 23 | CPU-only MoE request-mix, expert-skew, replica-profile replay evidence. |
| Online Boutique long-mix replay | 22 | Application-generality replay evidence for Online Boutique. |
| Continuous callgraph synthetic/replay | 18 | Dynamic call-graph and policy replay behavior. |
| Live MoE Kubernetes and policy smoke | 17 | Physical MoE deployments, policy smoke, and policy comparison runs. |
| Social Network live | 8 | Social Network smoke, live tc, and physical scale-series evidence. |
| Network dynamics validation | 5 | Network-trace replay and live tc validation evidence. |
| Other/precheck/observability | 5 | Cluster prechecks, observability setup, and supporting artifacts. |
| GDA synthetic/scalability | 4 | GDA overhead and scalability measurements. |
| GDA real application measurements | 2 | GDA measurements on real application benchmarks. |
| Online Boutique live | 2 | External Online Boutique live performance evidence. |

## Suggested Entry Points

- MoE benchmark reproduction: `benchmarks/moe-serving/README.md`
- MoE run family: `moe-longmix-*`, `moe-live-*`, `physical-moe-*`
- Online Boutique run family: `online-boutique-longmix-*`, `external-online-boutique-*`
- Network dynamics: `network-trace-*`, `live-tc-validation-*`, `live-tc-social-*`
- GDA overhead and scalability: `gda-*`
