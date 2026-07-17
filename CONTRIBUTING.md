# Contributing

Thank you for improving iDynamics. Keep changes focused on reproducible
research artifacts, benchmark adapters, policy interfaces, and documented
evidence boundaries.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev,analysis]"
```

Run the local checks before proposing a change:

```bash
make lint
make test
make artifact-smoke
```

Live-cluster tests and benchmark scripts are opt-in and require a prepared
testbed. Keep default tests offline and deterministic.

## Evidence Boundaries

New benchmark results should preserve a complete run ledger before being used
as evidence. If a result is synthetic, replay-only, compatibility-only, or
CPU-only, state that boundary in the relevant manifest and documentation.

Do not commit secret material, cluster access files, SSH keys, command histories, raw
environment dumps, unredacted Kubernetes objects, or cluster-specific node and
address data unless the data has been deliberately sanitized and is necessary
for reproduction.

## Third-Party Material

Do not vendor third-party benchmark source code into this repository. Add or
update `metadata.yaml` with the upstream URL, pinned commit, local checkout
path, license, and evidence limitations. Update `THIRD_PARTY_NOTICES.md` when
adding a benchmark, copied asset, or externally sourced data.

## Pull Requests

- Keep changes scoped and documented.
- Add focused tests for new code paths.
- Update `CHANGELOG.md` for user-visible changes.
- Update `CITATION.cff` only when citation metadata changes.
- Preserve the MIT license header and third-party notices where applicable.
