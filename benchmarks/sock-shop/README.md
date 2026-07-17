# Sock Shop

This package adapts Sock Shop for iDynamics compatibility runs. The upstream
repository is fetched at a pinned commit instead of vendored.

## Source And License

- Upstream: `https://github.com/microservices-demo/microservices-demo.git`
- Pinned commit: `9dff06fae4981921caec6a62393a6ebfce4b3e3f`
- License: Apache-2.0
- Local checkout: `external/benchmarks/sock-shop`
- Default manifests: `deploy/kubernetes/manifests`

## Scripts

Run any script with `--help`.

```bash
benchmarks/sock-shop/scripts/fetch.sh
benchmarks/sock-shop/scripts/deploy.sh --namespace idyn-sock-shop
benchmarks/sock-shop/scripts/smoke.sh --namespace idyn-sock-shop
benchmarks/sock-shop/scripts/load.sh --namespace idyn-sock-shop
benchmarks/sock-shop/scripts/collect.sh --namespace idyn-sock-shop
benchmarks/sock-shop/scripts/cleanup.sh --namespace idyn-sock-shop
```

`reproduce.sh` runs deploy, smoke, load, and collect in sequence. Set
`IDYN_CLEANUP=1` to delete the namespace afterward.

## Adapter Files

- `adapter/service_map.yaml`
- `adapter/workload_mix.yaml`
- `adapter/replica_profiles.yaml`
- `metadata.yaml`

## Known Limitations

- Upstream project is archived/deprecated; use as compatibility coverage.
- Older images and Kubernetes manifests may need cluster-specific patches.
- The service graph is REST-oriented and less representative of gRPC-heavy workloads.
