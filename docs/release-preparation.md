# Release Preparation

[Documentation index](index.md) | [Reproducibility](reproducibility.md) | [Changelog](../CHANGELOG.md)

This page describes release-candidate preparation for the public repository. It
does not authorize tagging, publishing, package upload, or external archive
publication.

## Release-Candidate Manifest

The release-candidate artifact manifest is
[`../reproducibility/release-candidate-artifact-manifest.yaml`](../reproducibility/release-candidate-artifact-manifest.yaml).
It records the package version, release state, included public paths, excluded
large-data categories, validation commands, and external archive requirements.

Before tagging a release candidate, confirm the manifest agrees with:

- `src/idynamics/_version.py`
- `setup.cfg`
- `CITATION.cff`
- `CHANGELOG.md`
- `RELEASE_NOTES.md`

## Public Repository Checks

Run these commands from the repository root and record only results that
actually completed:

```bash
make check
make artifact-smoke
make artifact-validate
python3 reproducibility/reproduce_all.py --mode full-cluster-plan
```

The full-cluster plan command lists live rerun steps only. It does not execute
cluster commands.

## Large-Data Archive Instructions

Large raw ledgers, environment snapshots, operational logs, and live-cluster
outputs should be archived outside the Git repository. Use a separate archive
only after the included run ledgers have been reviewed.

Recommended archive layout:

```text
idynamics-large-data-v0.1.0/
  MANIFEST.yaml
  SHA256SUMS
  runs/
    <run-id>/
      raw/
      processed/
      figures/
      logs/
  README.md
```

Archive requirements:

- Include only data that is intended for public artifact review.
- Exclude secret material, cluster access files, SSH material, private
  hostnames, command histories, and bearer-token material.
- Preserve run IDs used by `reproducibility/artifact-manifest.yaml`.
- Include a machine-readable `MANIFEST.yaml` with run IDs, source commands,
  collection date, software version or commit, evidence type, and claim
  boundary.
- Include `SHA256SUMS` covering every archived file.
- Record the external archive DOI or stable URL in release notes only after it
  exists.
- Do not copy large raw archives into this Git repository.

## Publication Hold Points

- Do not create a tag until package version, citation metadata, changelog,
  release notes, and artifact manifests agree.
- Do not publish package distributions until the sdist and wheel contents have
  been inspected.
- Do not publish external archives until their checksum and provenance manifests
  have been reviewed.
- Do not describe replay, synthetic, compatibility, or CPU-only evidence as live
  physical application performance.
