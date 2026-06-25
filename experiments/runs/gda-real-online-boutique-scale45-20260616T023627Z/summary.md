# gda-real-online-boutique-scale45-20260616T023627Z

Status: measured
Benchmark: Online Boutique / Google Microservices Demo
Namespace: `gda-real-online-boutique-scale45-20260616t023627z`
Scale: `scale45`

Source commit: `5096a85b2f3bf41bef53363cfe5478d5b86ac701`

## Load

- Requests: 2511
- Throughput: 55.69 req/s
- Hard error rate: 0.0000
- p50/p95/p99 latency: 115.57/201.83/628.86 ms

## GDA Overhead

- Services: 12
- Active edges median/max: 15/15
- Median density: 0.113636
- Sparse/dense logical Prometheus queries: 2/264
- Query reduction: 132.0x
- GDA total p50/p95: 10.782/11.405 ms
- Graph-build p50/p95: 0.259/0.369 ms
- Peak Python memory p95: 0.012268 MiB

## Pod/Node Occupancy

- Worker nodes selected: 45
- Actual app pods: 11
- Ready app pods: 11
- Non-empty worker nodes: 7
- Occupancy ratio: 0.1556
- Evidence label: worker-pool/candidate-space evidence

## Claim Boundary

Use measured rows only for Algorithm 1 live benchmark overhead. Blocked rows document deployment or telemetry feasibility, not benchmark performance.
