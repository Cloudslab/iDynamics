# Installation

[Documentation index](index.md) | [Quickstart](quickstart.md) | [Troubleshooting](troubleshooting.md)

iDynamics can be installed for offline development without a cluster. Live
benchmark and network-emulation work adds Kubernetes, service-mesh, and node
permission requirements.

## Local Python Setup

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev,analysis]"
```

Verify the package and offline tests:

```bash
make discovery
make unit
```

Run the full local maintenance suite and build source and wheel artifacts:

```bash
make lint
make build
```

`make lint` runs ruff when it is installed, Python bytecode compilation,
shellcheck, codespell, and local Markdown-link validation. In air-gapped
environments without ruff, `make ruff` falls back to syntax validation so the
rest of the local checks can still run. `make pre-commit` runs the configured
hooks through `pre-commit` when installed, or the equivalent local targets
directly when it is unavailable.

## Optional Cluster Extras

Install the cluster extra when running Kubernetes helpers from Python:

```bash
python3 -m pip install -e ".[cluster]"
```

Live-cluster scripts also expect command-line tools that are not installed by
Python packaging:

- `kubectl` for deploy, smoke, load, collect, and cleanup scripts;
- `helm` for the DeathStarBench Social Network adapter;
- `curl` for HTTP smoke checks;
- `git` for fetching pinned third-party benchmark sources.

Network emulation requires Linux worker nodes with traffic-control support and
permissions to apply `tc` qdisc and filter changes. Run these steps only on
testbed nodes where you can safely reset network shaping.

Live Kubernetes tests are opt-in. The default `pytest` and `make test` paths
skip tests marked `live_cluster`; run the live target only from a prepared
testbed. If the public test suite does not include live-cluster tests, the
target exits cleanly with a skip message:

```bash
make live-cluster-test
```

## Benchmark Source Checkouts

Third-party applications are not vendored. Fetch scripts clone pinned upstream
commits into `external/benchmarks/`:

```bash
benchmarks/online-boutique/scripts/fetch.sh
benchmarks/social-network/scripts/fetch.sh
```

For air-gapped or pre-fetched environments, set `IDYN_SKIP_FETCH=1` and ensure
the expected checkout path already exists.

## Artifact Tools

The data-only artifact path uses committed CSV, YAML, and Python scripts. It
does not require a live cluster:

```bash
make artifact-smoke
make artifact-validate
```

`make artifact-all` regenerates all expected tables and figures under
`reproducibility/generated/`.

## Package Namespaces

Prefer modern imports:

```python
from idynamics.policies import make_policy
from idynamics.network.traces import BurstCorrelatedProvider
```

Legacy imports through `iDynamicsPackagesModules` remain available for existing
scripts, but new integrations should use `idynamics` unless a compatibility
module is specifically required.
