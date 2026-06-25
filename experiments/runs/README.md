# Cleaned Run Artifacts

This directory contains 118 cleaned experiment run folders. The folders are
kept as lightweight references for readers of `IEEE_TSC_iDynamics_Revision.pdf`.

## What Was Kept

Common useful files:

- `summary.md`: run-level result, scope, and limitations.
- `config.yaml`: parameters, scale, workload, policy, and evidence labels.
- `raw/`: manifests, traces, load-generator CSVs, or captured cluster state.
- `processed/`: metrics, summaries, and table-ready CSV/JSON outputs.
- `env/`: environment snapshots when they help interpret the run.

## What Was Removed

The cleaned copy removes files that are not useful for paper readers:

- `paper_claims.md`
- `codex_model.txt`
- `git_sha.txt`
- `git_status.txt`
- `commands.log`
- `logs/`
- `figures/`
- run folders whose `summary.md` reported `Status: blocked`

The full uncleaned ledgers are preserved separately outside this repository.

## Run Families

| Family | Count | Typical purpose |
| --- | ---: | --- |
| MoE long-mix replay | 23 | CPU-only MoE request-mix, expert-skew, replica-profile replay evidence. |
| Online Boutique long-mix replay | 22 | Application-generality replay evidence for Online Boutique. |
| Continuous callgraph synthetic/replay | 18 | Dynamic call-graph and policy replay behavior. |
| Social Network live | 12 | Social Network smoke, live tc, or GDA evidence. |
| Live MoE Kubernetes | 12 | Physical MoE deployments and policy comparisons. |
| GDA synthetic/scalability | 7 | GDA overhead and scalability measurements. |
| Network dynamics validation | 6 | Network-trace replay and live tc validation evidence. |
| Online Boutique live/GDA | 3 | External Online Boutique live or GDA measurements. |
| Other/precheck/observability | 15 | Cluster prechecks, observability setup, external attempts, and supporting artifacts. |

## Suggested Entry Points

- MoE benchmark reproduction: `benchmarks/moe-serving/README.md`
- MoE run family: `moe-longmix-*`, `moe-live-*`, `physical-moe-*`
- Online Boutique run family: `online-boutique-longmix-*`, `external-online-boutique-*`
- Network dynamics: `network-trace-*`, `live-tc-validation-*`, `live-tc-social-*`
- GDA overhead and scalability: `gda-*`

When a remaining run has a status such as `failed` or `superseded` in
`summary.md`, treat it as diagnostic or contextual evidence rather than a
primary reported result.
