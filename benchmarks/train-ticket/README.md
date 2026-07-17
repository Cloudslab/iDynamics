# TrainTicket

This package adapts TrainTicket for iDynamics compatibility runs. The upstream
repository is fetched at a pinned commit instead of vendored.

## Source And License

- Upstream: `https://github.com/FudanSELab/train-ticket.git`
- Pinned commit: `313886e99befb94be6cd45f085c98e0019f59829`
- License: Apache-2.0
- Local checkout: `external/benchmarks/train-ticket`
- Default manifest directory: `deployment/kubernetes-manifests/k8s-with-istio`

## Scripts

Run any script with `--help`.

```bash
benchmarks/train-ticket/scripts/fetch.sh
benchmarks/train-ticket/scripts/deploy.sh --namespace idyn-train-ticket
benchmarks/train-ticket/scripts/smoke.sh --namespace idyn-train-ticket
benchmarks/train-ticket/scripts/load.sh --namespace idyn-train-ticket
benchmarks/train-ticket/scripts/collect.sh --namespace idyn-train-ticket
benchmarks/train-ticket/scripts/cleanup.sh --namespace idyn-train-ticket
```

`reproduce.sh` runs deploy, smoke, load, and collect in sequence. Set
`IDYN_CLEANUP=1` to delete the namespace afterward.

## Adapter Files

- `adapter/service_map.yaml`
- `adapter/workload_mix.yaml`
- `adapter/replica_profiles.yaml`
- `metadata.yaml`

## Known Limitations

- Large service and database footprint; use larger clusters and longer rollout timeouts.
- This package provides HTTP smoke/load scaffolding, not a validated full workload trace.
- Treat as complex compatibility evidence unless a full run directory is produced.
