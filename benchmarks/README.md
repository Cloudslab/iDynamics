# Benchmark Packaging

This directory contains benchmark adapter packages for iDynamics. Third-party
applications are not vendored here; their scripts fetch pinned upstream commits
into `external/benchmarks/` and then apply iDynamics namespace, telemetry, and
load wrappers.

Each benchmark folder has:

- `README.md`
- `metadata.yaml`
- `adapter/service_map.yaml`
- `adapter/workload_mix.yaml`
- `adapter/replica_profiles.yaml`
- `scripts/fetch.sh`
- `scripts/deploy.sh`
- `scripts/smoke.sh`
- `scripts/load.sh`
- `scripts/collect.sh`
- `scripts/cleanup.sh`
- `scripts/reproduce.sh`

Run any script with `--help` for supported flags. Namespaces are restricted to
the `idyn-*` pattern to avoid accidental deletion of shared cluster namespaces.
