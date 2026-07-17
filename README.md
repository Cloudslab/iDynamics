# iDynamics

[![CI](https://github.com/Cloudslab/iDynamics/actions/workflows/ci.yml/badge.svg)](https://github.com/Cloudslab/iDynamics/actions/workflows/ci.yml)
[![Artifact Smoke](https://github.com/Cloudslab/iDynamics/actions/workflows/artifact-smoke.yml/badge.svg)](https://github.com/Cloudslab/iDynamics/actions/workflows/artifact-smoke.yml)
[![Link Check](https://github.com/Cloudslab/iDynamics/actions/workflows/links.yml/badge.svg)](https://github.com/Cloudslab/iDynamics/actions/workflows/links.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](pyproject.toml)

iDynamics is a configurable emulation and reproducibility framework for
evaluating microservice scheduling policies under cloud-edge dynamics. It
combines changing application call graphs, network latency and bandwidth
matrices, benchmark adapters, and auditable run ledgers so placement policies
can be tested against repeatable dynamic conditions.

![Framework of iDynamics](iDynamics-framework_v4.png)

## Purpose

The repository supports research artifact use for cloud-edge microservice
scheduling. It provides offline policy and artifact checks that run without
Kubernetes, plus optional live-cluster helpers for prepared testbeds.
The built-in policy vocabulary includes CGA, the call-graph-aware planner
represented by `Policy1TrafficAffinity`, and HDA, the hybrid-dynamics-aware
planner represented by `Policy4HybridDynamics`.

## Architecture

iDynamics is organized around four public surfaces:

- **Graph Dynamics Analyzer (GDA):** builds sparse weighted service graphs from
  application telemetry or adapter data and reports graph-movement metrics.
- **Network Dynamics Manager (NDM):** generates, replays, measures, and, on
  prepared Linux testbeds, applies latency and bandwidth dynamics.
- **Scheduling Policy Extender (SPE):** exposes a policy interface for CGA,
  HDA, auxiliary latency-aware and bandwidth-aware examples, and custom
  placement planners.
- **Run ledgers and artifacts:** preserve configuration, commands, code state,
  raw outputs, processed outputs, and claim boundaries for reproducibility.

The modern Python API lives under `idynamics`. The
`iDynamicsPackagesModules` namespace remains available for legacy compatibility.

## Capabilities

- Offline policy planning with manuscript-facing CGA and HDA planners, plus
  auxiliary latency-critical-path and bandwidth-payload-aware examples.
- Synthetic and replayable latency/bandwidth trace providers.
- Sparse GDA helpers for call-graph construction, traffic stress, edge churn,
  entropy, skew, and related control-plane metrics.
- Benchmark adapters for Social Network, Online Boutique, CPU-only MoE Serving,
  DeathStarBench Hotel, TrainTicket, and Sock Shop.
- Data-only regeneration for the committed reproducibility artifacts.
- Optional Kubernetes benchmark scripts for fetch, deploy, smoke, load, collect,
  cleanup, and dry-run planning.

## Supported Stack

- Python 3.10 or newer with `setuptools` and `wheel`.
- Offline checks: `make`, `pytest`, and the repository-local Python package.
- Optional analysis extras: `matplotlib`, `networkx`, `numpy`, `pandas`,
  `prometheus-api-client`, and `seaborn`.
- Optional cluster work: Kubernetes, `kubectl`, `curl`, `git`, and `helm` for
  Helm-based adapters.
- Optional live NDM work: Linux worker nodes with traffic-control support and
  permission to apply and clear `tc` qdisc and filter rules.

## 15-Minute Artifact Quickstart

This path runs locally from the repository root and does not deploy Kubernetes
resources. It uses existing system packages so the artifact smoke path can run
without network access; see [Installation](docs/installation.md) for isolated
development environments.

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python3 -m pip install -e . --no-build-isolation
python3 scripts/policies/run_policy.py --policy policy4 --demo moe --output /tmp/idynamics-policy4.json
python3 -m json.tool /tmp/idynamics-policy4.json
make unit
make artifact-smoke
```

The policy command writes a CPU-only MoE-style HDA placement plan. The artifact
smoke target regenerates a representative table and figure from committed data,
then validates artifact structure and checksums.

## Cluster Quickstart

Start with non-mutating cluster plans and dry-run benchmark commands. Remove
`--dry-run` only on a prepared testbed where the `idyn-*` namespace, image
access, service mesh, and cleanup requirements are understood.

```bash
python3 reproducibility/reproduce_all.py --mode full-cluster-plan
IDYN_CLEANUP=1 benchmarks/moe-serving/scripts/reproduce.sh --namespace idyn-moe-serving --duration 30 --concurrency 4 --dry-run
```

The MoE Serving command exercises the same deploy, smoke, load, collect, and
cleanup flow used by live benchmark scripts, but prints the operations instead
of mutating a cluster.

## Benchmarks

| Benchmark | Adapter | Evidence role |
| --- | --- | --- |
| Social Network | `benchmarks/social-network` | Real benchmark adapter; performance claims require a complete run ledger. |
| Online Boutique | `benchmarks/online-boutique` | Primary external application adapter for live or replay-backed evidence. |
| MoE Serving | `benchmarks/moe-serving` | Repository-local CPU-only MoE-style benchmark; no GPU or model-weight claim. |
| DeathStarBench Hotel | `benchmarks/deathstar-hotel` | Compatibility adapter unless backed by a full run ledger. |
| TrainTicket | `benchmarks/train-ticket` | Large-footprint compatibility adapter unless a validated workload trace and ledger are supplied. |
| Sock Shop | `benchmarks/sock-shop` | Archived-upstream compatibility adapter. |

See [Benchmark Guide](docs/benchmark-guide.md) for pinned upstream commits,
licenses, namespaces, and script contracts.

## Reproducibility

The `reproducibility/` tree is a data-only artifact package for Tables I-VIII
and Figures 7-9. Its manifests separate live physical evidence, replay evidence,
synthetic control-plane evidence, compatibility evidence, and CPU-only MoE
evidence. Use the `claim_boundary` fields in
[`reproducibility/manifest.yaml`](reproducibility/manifest.yaml) and the
[Paper and Evidence Guide](docs/paper.md) before using generated outputs to
support results.

Data-only regeneration does not rerun the physical cluster. Public
full-cluster plans are listed only when the corresponding scripts are shipped,
so live experiments can be rerun only on suitable testbeds and then archived
through complete run ledgers.

## Limitations

- iDynamics is a research artifact, not a production Kubernetes scheduler.
- Replay and synthetic control-plane outputs do not prove live application
  latency or policy superiority.
- The CPU-only MoE benchmark models routing and service communication; it does
  not evaluate GPU scheduling, model weights, or production inference serving.
- Live NDM emulation is testbed-specific and requires safe network-shaping
  permissions plus cleanup discipline.
- Legacy NDM validation artifacts preserve their documented evidence boundary;
  not every historical intermediate ledger is present in the public package.

## Documentation

- [Documentation index](docs/index.md)
- [Architecture](docs/architecture.md)
- [Installation](docs/installation.md)
- [Quickstart](docs/quickstart.md)
- [Configuration](docs/configuration.md)
- [Policy development](docs/policy-development.md)
- [Benchmark guide](docs/benchmark-guide.md)
- [Reproducibility](docs/reproducibility.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Paper and evidence guide](docs/paper.md)
- [Changelog and versioning](CHANGELOG.md)
- [Release notes](RELEASE_NOTES.md)
- [Release preparation](docs/release-preparation.md)

## Citation

```bibtex
@misc{chen2025idynamicsnovelframeworkevaluating,
  title={iDynamics: A Configurable Emulation Framework for evaluating Microservice Scheduling Policies under Controllable Cloud-Edge Dynamics},
  author={Ming Chen and Muhammed Tawfiqul Islam and Maria Rodriguez Read and Rajkumar Buyya},
  year={2025},
  eprint={2503.16029},
  archivePrefix={arXiv},
  primaryClass={cs.DC},
  url={https://arxiv.org/abs/2503.16029}
}
```

## Contributing

Keep changes aligned with the existing package layout and evidence taxonomy.
New policies should implement the SPE protocol, include focused offline tests,
and document how their claims differ from CGA and HDA. New benchmark results
should preserve a complete run ledger before they are summarized as evidence.

## License

This repository is licensed under the [MIT License](LICENSE). Third-party
benchmark sources fetched under `external/benchmarks/` retain their upstream
licenses and pinned source provenance; see
[Third-Party Notices](THIRD_PARTY_NOTICES.md).
