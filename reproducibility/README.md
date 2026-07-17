# Reproducibility Artifacts

This directory contains the data-only artifact package for manuscript Tables
I-VIII and Figures 7-9.

Detailed documentation:

- [Reproducibility guide](../docs/reproducibility.md)
- [Paper and evidence guide](../docs/paper.md)
- [Benchmark guide](../docs/benchmark-guide.md)

## Contents

- `manifest.yaml` is the machine-readable top-level index.
- `artifact-manifest.yaml` maps artifacts to raw and processed inputs where
  applicable.
- `items/` contains one folder per table or figure. Each folder has curated
  `data/`, deterministic `expected/` outputs, `manifest.yaml`, `README.md`,
  `run.sh`, `scripts/`, and `checksums.sha256`.
- `reproduce_all.py` regenerates expected tables and SVG figures from committed
  curated data.
- `validate_artifacts.py` checks structure, checksums, public-text hygiene, and
  regenerated output equivalence.
- `diagrams/` contains small conceptual diagram assets used by the public docs
  and artifact inspection.

## Commands

From the repository root:

```bash
make artifact-smoke
make artifact-all
make artifact-validate
```

The offline artifact path does not require a live cluster. Public item
manifests list full-cluster rerun commands only when the corresponding scripts
are shipped in this repository. The current plan can be inspected with:

```bash
python3 reproducibility/reproduce_all.py --mode full-cluster-plan
```

## Evidence Types

Artifact interpretation should keep live physical, replay, synthetic
control-plane, compatibility, and CPU-only MoE evidence separate. The
`claim_boundary` field in each item manifest defines what that artifact can and
cannot support.
