# Reproducibility

[Documentation index](index.md) | [Paper and evidence guide](paper.md) | [Troubleshooting](troubleshooting.md)

The `reproducibility/` tree is a data-only artifact package for paper-facing
tables and figures. It is designed to regenerate expected outputs from committed
curated inputs without requiring a live cluster.

## Directory Contract

- `reproducibility/manifest.yaml`: top-level machine-readable artifact index.
- `reproducibility/artifact-manifest.yaml`: expanded mapping to raw and
  processed run inputs where applicable.
- `reproducibility/items/<item>/data`: committed curated input data.
- `reproducibility/items/<item>/expected`: expected regenerated table or figure
  output.
- `reproducibility/items/<item>/run.sh`: data-only regeneration entry point.
- `reproducibility/items/<item>/checksums.sha256`: checksum inventory.
- `reproducibility/reproduce_all.py`: multi-artifact regeneration driver.
- `reproducibility/validate_artifacts.py`: structure, checksum, hygiene, and
  regenerated-output validator.

## Data-Only Commands

From the repository root:

```bash
make artifact-smoke
make artifact-all
make artifact-validate
```

To regenerate one item directly:

```bash
bash reproducibility/items/table-v-network-trace-provider/run.sh --output-dir /tmp/idyn-table-v
```

## Full-Cluster Plans

Each item manifest can include a `full_cluster_rerun` plan only when the
corresponding public scripts are shipped in this repository. List the current
plan without running cluster commands:

```bash
python3 reproducibility/reproduce_all.py --mode full-cluster-plan
```

When present, these plans describe the live steps needed to regenerate upstream
ledgers. They are not executed by the data-only artifact commands.

## Evidence Types

Keep these evidence types separate when writing results or reports:

| Evidence type | What it can support | What it cannot support by itself |
| --- | --- | --- |
| Live physical | Claims about the named testbed, workload, telemetry, or traffic-control validation actually run. | General performance claims outside the run configuration. |
| Replay | Deterministic regeneration from captured or generated traces and committed data. | Claims that a live application reran during regeneration. |
| Synthetic control-plane | Algorithmic scaling, query-count, trace-generation, and local planner behavior. | End-to-end application latency on a physical cluster. |
| Compatibility | Adapter packaging, deployment scaffolding, smoke tests, and collection plumbing. | Comparative scheduler or application performance. |
| CPU-only MoE | MoE-style routing, fan-out, fan-in, payload, cache, and CPU-work behavior in the local benchmark. | GPU scheduling, model-serving throughput, or production inference behavior. |

## Artifact Boundaries

The artifact manifests record claim boundaries for each table and figure. A few
examples:

- Table III separates real GDA rows from synthetic graph-construction rows.
- Table V describes trace-provider matrix statistics, not application latency or
  scheduler quality.
- Table VIII is replay/model/control-plane evidence over generated call-graph
  traces, not live physical application latency.
- Figure 9 includes Online Boutique and the CPU-only MoE-style benchmark under a
  common adapter and replay schema.

Use the `claim_boundary` fields in item manifests as the source of truth when
deciding whether a regenerated artifact can support a statement.

## Run Ledgers

Live experiments should write complete ledgers under `experiments/runs/<run-id>`
before their outputs are summarized or copied into curated artifacts. Required
ledger files are documented in [Architecture](architecture.md#run-ledgers).

For new runs:

```python
from idynamics.ledger.run import init_run_ledger

ledger = init_run_ledger("my-run-id", purpose="benchmark smoke")
```

Archive raw outputs under `raw/`, derived outputs under `processed/`, final
plots under `figures/`, and operational logs under `logs/`.

## Validation

Run validation before publishing artifact updates:

```bash
python3 reproducibility/validate_artifacts.py
```

If validation fails, inspect the named item first. Common causes are stale
checksums, changed expected output, missing generated files, or an artifact
folder that no longer matches the manifest.
