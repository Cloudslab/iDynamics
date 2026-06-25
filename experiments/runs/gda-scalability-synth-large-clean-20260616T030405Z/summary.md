# gda-scalability-synth-large-clean-20260616T030405Z

Status: completed

## Purpose
Synthetic/control-plane overhead comparison for legacy dense GDA pair scanning versus sparse active-edge construction.

## Result
- Largest synthetic service graph: 50000 services.
- Active edges at largest size: 200000.
- Sparse Prometheus query count at largest size: 2.
- Dense comparison measured through: 1000 services.
- Sparse graph-build p95 at largest size: 2696.727 ms.
- Sparse peak Python memory p95 at largest size: 121.039 MiB.
- Dense-vs-sparse query reduction at largest size: 2499950000.0x.

