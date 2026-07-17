# DeathStarBench Social Network

This package adapts DeathStarBench Social Network for iDynamics benchmark runs.
The upstream repository is fetched on demand instead of vendored.

## Source And License

- Upstream: `https://github.com/delimitrou/DeathStarBench.git`
- Pinned commit: `6ecb09706140f8730b5385c08f1386c654c3c526`
- License: Apache-2.0
- Local checkout: `external/benchmarks/deathstarbench`
- Upstream subdirectory: `socialNetwork`

## Scripts

Run any script with `--help`.

```bash
benchmarks/social-network/scripts/fetch.sh
benchmarks/social-network/scripts/deploy.sh --namespace idyn-social-network
benchmarks/social-network/scripts/smoke.sh --namespace idyn-social-network
benchmarks/social-network/scripts/load.sh --namespace idyn-social-network
benchmarks/social-network/scripts/collect.sh --namespace idyn-social-network
benchmarks/social-network/scripts/cleanup.sh --namespace idyn-social-network
```

`reproduce.sh` runs deploy, smoke, load, and collect in sequence. Set
`IDYN_CLEANUP=1` to delete the namespace afterward.

## Adapter Files

- `adapter/service_map.yaml`
- `adapter/workload_mix.yaml`
- `adapter/replica_profiles.yaml`
- `metadata.yaml`

## Known Limitations

- Stateful MongoDB, Redis, Memcached, and Jaeger components can dominate startup time.
- The upstream Helm chart may initialize data at pod startup.
- Manual load output is operational evidence unless archived with full run context.
