# Maintainer Checklist

Use this checklist before merging public repository changes or preparing a
release candidate. It is intentionally conservative because this repository
contains both offline research artifacts and optional live-cluster tooling.

## Pull Requests

- Confirm the change is scoped to public repository content.
- Confirm docs, tests, benchmark metadata, and reproducibility manifests changed
  together when behavior or artifact boundaries changed.
- Run the appropriate local checks and record only checks that actually ran.
- Review new public text for unsupported claims, private paths, credentials,
  cluster access details, and raw operational logs.
- Confirm new benchmark results have complete run ledgers before they are
  summarized as evidence.
- Confirm external benchmark sources remain fetched under `external/` and keep
  their upstream licenses and pinned provenance.

## Release Candidates

- Confirm `src/idynamics/_version.py`, `setup.cfg`, `CITATION.cff`,
  `CHANGELOG.md`, `RELEASE_NOTES.md`, and
  `reproducibility/release-candidate-artifact-manifest.yaml` agree on the
  intended package version.
- Run `make check` from a clean environment before tagging.
- Run `make artifact-smoke` and `make artifact-validate` before publishing an
  artifact release.
- Inspect `python3 reproducibility/reproduce_all.py --mode full-cluster-plan`
  output before scheduling any live-cluster reruns.
- Build the package with `python -m build` and inspect the generated sdist and
  wheel contents before upload.
- Verify the external large-data archive has a checksum manifest, provenance
  manifest, and no credentials or access files.
- Create tags, GitHub releases, and external archive records only after
  authorization from the project maintainers.

## Evidence Boundary Review

- Live physical evidence must identify the exact testbed shape, workload,
  telemetry source, and run ledger.
- Replay evidence must identify the committed or archived trace source.
- Synthetic control-plane evidence must not be described as application
  end-to-end latency.
- Compatibility evidence must not be described as scheduler performance.
- CPU-only MoE evidence must not be described as GPU scheduling or production
  model-serving evidence.
