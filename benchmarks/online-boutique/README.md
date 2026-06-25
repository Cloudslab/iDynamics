# Online Boutique Benchmark Adapter

Online Boutique is the primary external benchmark adapter for iDynamics. It uses
Google's Microservices Demo release manifests, the in-cluster Locust
loadgenerator, Istio telemetry, and the repository's ledger-backed runner.

## Quick Start

Prerequisites:

- Local source checkout at `/home/ubuntu/idyn-external/online-boutique`
- Worker labels such as `idynamics.dev/scale10=true`
- `kubectl` access to the target cluster
- Istio Prometheus available as `istio-system/svc/prometheus` for call-graph metrics

Run a full reproducible GDA overhead ledger:

```bash
IDYN_SCALE=scale45 IDYN_CLEANUP=1 benchmarks/online-boutique/scripts/reproduce.sh
```

By default, the runner creates
`experiments/runs/gda-real-online-boutique-<scale>-<timestamp>/` with config,
commands, raw Kubernetes data, load metrics, Prometheus GDA samples, processed
overhead summaries, and paper-claim boundaries. Set `IDYN_GDA_OVERHEAD=0` to
use the older Online Boutique external smoke runner.

## Script Surface

- `scripts/deploy.sh`: apply upstream manifests into a namespace for manual use.
- `scripts/smoke.sh`: port-forward `frontend` and perform HTTP smoke checks.
- `scripts/run_load.sh`: run bounded HTTP load through `frontend`.
- `scripts/collect_metrics.sh`: collect Kubernetes and optional Prometheus data.
- `scripts/cleanup.sh`: delete the benchmark namespace.
- `scripts/reproduce.sh`: preferred ledger-backed experiment entry point.

## Claim Boundary

Use only run-ledger-backed results for paper claims. Manual deploy/smoke/load
scripts are operational helpers and do not create sufficient evidence by
themselves.
