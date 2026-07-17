# DeathStarBench Hotel Reservation

This package adapts DeathStarBench Hotel Reservation for iDynamics compatibility
runs. The upstream repository is fetched on demand instead of vendored.

## Source And License

- Upstream: `https://github.com/delimitrou/DeathStarBench.git`
- Pinned commit: `6ecb09706140f8730b5385c08f1386c654c3c526`
- License: Apache-2.0
- Local checkout: `external/benchmarks/deathstarbench`
- Upstream subdirectory: `hotelReservation`

## Scripts

Run any script with `--help`.

```bash
benchmarks/deathstar-hotel/scripts/fetch.sh
benchmarks/deathstar-hotel/scripts/deploy.sh --namespace idyn-dsb-hotel
benchmarks/deathstar-hotel/scripts/smoke.sh --namespace idyn-dsb-hotel
benchmarks/deathstar-hotel/scripts/load.sh --namespace idyn-dsb-hotel
benchmarks/deathstar-hotel/scripts/collect.sh --namespace idyn-dsb-hotel
benchmarks/deathstar-hotel/scripts/cleanup.sh --namespace idyn-dsb-hotel
```

`reproduce.sh` runs deploy, smoke, load, and collect in sequence. Set
`IDYN_CLEANUP=1` to delete the namespace afterward.

## Adapter Files

- `adapter/service_map.yaml`
- `adapter/workload_mix.yaml`
- `adapter/replica_profiles.yaml`
- `metadata.yaml`

## Known Limitations

- Upstream manifests include stateful database and cache components.
- Consul and Jaeger are deployed with the application and can affect telemetry.
- Treat as compatibility evidence unless a full run directory is produced.
