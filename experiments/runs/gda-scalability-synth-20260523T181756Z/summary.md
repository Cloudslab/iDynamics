# gda-scalability-synth-20260523T181756Z

Status: completed

## Purpose
Synthetic/control-plane overhead comparison for legacy dense GDA pair scanning versus sparse active-edge construction.

## Result
- Largest synthetic service graph: 5000 services.
- Active edges at largest size: 20000.
- Sparse Prometheus query count at largest size: 2.
- Dense comparison measured through: 1000 services.
- Sparse graph-build p95 at largest size: 160.521 ms.
- Sparse peak Python memory p95 at largest size: 11.031 MiB.
- Dense-vs-sparse query reduction at largest size: 24995000.0x.

