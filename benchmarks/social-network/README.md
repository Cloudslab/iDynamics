# DeathStarBench Social Network Benchmark Adapter

This adapter targets the upstream DeathStarBench Social Network Helm chart in
`/home/ubuntu/idyn-external/deathstarbench/socialNetwork`. It is intended for
live GDA Algorithm 1 overhead evaluation on the current Kubernetes cluster.

## Quick Start

```bash
IDYN_SCALE=scale45 IDYN_CLEANUP=1 benchmarks/social-network/scripts/reproduce.sh
```

The reproducible path writes a ledger under
`experiments/runs/gda-real-social-network-<scale>-<timestamp>/` containing
deployment commands, raw Kubernetes state, load requests, Prometheus query
records, GDA overhead samples, processed summaries, and claim boundaries.

## Manual Operations

- `scripts/deploy.sh`: install the upstream Helm chart into an Istio-injected namespace and patch deployments to the selected iDynamics worker pool.
- `scripts/run_load.sh`: port-forward `nginx-thrift` and issue DeathStarBench-style compose/read requests.
- `scripts/collect_metrics.sh`: collect Kubernetes state and optional Prometheus service-to-service telemetry.
- `scripts/cleanup.sh`: uninstall the Helm release and delete the namespace.
- `scripts/reproduce.sh`: preferred ledger-backed experiment entry point.

