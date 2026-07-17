# Changelog

All notable changes to this repository should be recorded here.

The format follows the spirit of Keep a Changelog, and version numbers follow
Semantic Versioning for the Python package surface.

## Unreleased

### Added

- Maintenance checks for ruff, pytest, package builds, shellcheck, codespell,
  pre-commit, and local Markdown links.
- GitHub Actions workflows for CI, artifact smoke reproduction, link checking,
  and opt-in Kubernetes integration tests.
- GitHub issue forms, pull request template, maintainer checklist, repository
  topic recommendations, and README badges.
- Release notes, release-preparation documentation, and a release-candidate
  artifact manifest with large-data archive requirements.

## 0.1.0

### Added

- Initial public research artifact package with the `idynamics` API,
  legacy compatibility namespace, offline tests, benchmark adapters, and
  data-only reproducibility artifacts.

## Versioning Guidance

- The package version is defined in `src/idynamics/_version.py` and consumed by
  `setup.cfg`; update that file and this changelog in the same release commit.
- Use patch releases for compatible bug fixes and maintenance-only changes.
- Use minor releases for new public APIs, new adapters, or new artifact entries
  that preserve existing behavior.
- Use major releases for incompatible API, artifact-schema, or command-line
  changes.
- Do not create a release tag until the CI, package build, tests, artifact
  smoke reproduction, and link check pass for the intended commit.
