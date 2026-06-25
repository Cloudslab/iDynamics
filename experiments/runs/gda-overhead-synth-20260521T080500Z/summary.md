# gda-overhead-synth-20260521T080500Z

Status: completed

## Purpose
Synthetic control-plane overhead comparison for legacy dense GDA pair scanning versus sparse active-edge construction.

## Result
- Largest synthetic service graph: 1000 services.
- Active edges at largest size: 4000.
- Legacy Prometheus query count at largest size: 1998000.
- Sparse Prometheus query count at largest size: 2.
- Query reduction ratio at largest size: 999000.0x.
- Median CPU-loop ratio at largest size: 14.41x.

## Limitations
- This is a synthetic/control-plane overhead run, not a physical >10-node cluster experiment.
- Results support Algorithm 1 overhead/scalability discussion, not application SLA claims.
