# Mapped Items

Each folder maps to one manuscript table or evaluation figure listed in `../manifest.yaml`.

Folder contract:

- `data/` contains the minimum curated inputs needed for offline regeneration.
- `expected/` contains the deterministic regenerated table or SVG output.
- `manifest.yaml` declares exact local inputs, expected outputs, source run IDs, claim boundaries, and full-cluster rerun notes.
- `run.sh` regenerates the artifact from local curated data without hard-coded absolute paths.
- `checksums.sha256` records the curated inputs, scripts, manifests, and expected outputs.
