# Online Boutique

This package adapts Google's Online Boutique microservices demo for iDynamics
benchmark runs. The upstream source is fetched at a pinned commit instead of
vendored into this repository.

## Source And License

- Upstream: `https://github.com/GoogleCloudPlatform/microservices-demo.git`
- Pinned commit: `5096a85b2f3bf41bef53363cfe5478d5b86ac701`
- License: Apache-2.0
- Local checkout: `external/benchmarks/online-boutique`
- Default manifest: `release/kubernetes-manifests.yaml`

## Scripts

Run any script with `--help`.

```bash
benchmarks/online-boutique/scripts/fetch.sh
benchmarks/online-boutique/scripts/deploy.sh --namespace idyn-online-boutique
benchmarks/online-boutique/scripts/smoke.sh --namespace idyn-online-boutique
benchmarks/online-boutique/scripts/load.sh --namespace idyn-online-boutique
benchmarks/online-boutique/scripts/collect.sh --namespace idyn-online-boutique
benchmarks/online-boutique/scripts/cleanup.sh --namespace idyn-online-boutique
```

`reproduce.sh` runs deploy, smoke, load, and collect in sequence. Set
`IDYN_CLEANUP=1` to delete the namespace afterward.

## Adapter Files

- `adapter/service_map.yaml`
- `adapter/workload_mix.yaml`
- `adapter/replica_profiles.yaml`
- `metadata.yaml`

## Known Limitations

- Release manifests require image registry access from the target cluster.
- The HTTP frontend load path does not directly exercise every gRPC service edge.
- Optional cloud-provider overlays are outside this package.
