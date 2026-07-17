# Release Notes

## 0.1.0 Candidate

Status: release-preparation notes only. This document does not imply that a
release tag, package upload, or external archive has been published.

### Package And Documentation

- Adds the `idynamics` Python package surface with legacy compatibility modules.
- Provides documentation for installation, quickstarts, configuration,
  architecture, policy development, benchmark adapters, reproducibility, and
  evidence boundaries.
- Includes maintenance metadata for citation, licensing, contribution,
  security, third-party notices, changelog entries, and public repository
  presentation.

### Reproducibility Artifacts

- Provides a data-only artifact package for manuscript Tables I-VIII and
  Figures 7-9.
- Includes curated inputs, deterministic expected outputs, checksums, item
  manifests, and regeneration scripts for committed artifacts.
- Separates live physical, replay, synthetic control-plane, compatibility, and
  CPU-only MoE evidence through manifest claim boundaries.

### Benchmark Adapters

- Includes adapters and scripts for Social Network, Online Boutique, CPU-only
  MoE Serving, DeathStarBench Hotel, TrainTicket, and Sock Shop.
- Keeps live-cluster commands opt-in and documents dry-run and cleanup paths.

### Required Verification Before Publication

- `make check`
- `make artifact-smoke`
- `make artifact-validate`
- `python3 reproducibility/reproduce_all.py --mode full-cluster-plan`
- External large-data archive checksum and provenance review, when publishing
  archived run ledgers outside the Git repository.
