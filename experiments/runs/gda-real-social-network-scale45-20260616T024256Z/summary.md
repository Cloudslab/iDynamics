# gda-real-social-network-scale45-20260616T024256Z

Status: measured
Benchmark: DeathStarBench Social Network
Namespace: `gda-real-social-network-scale45-20260616t024256z`
Scale: `scale45`

Source commit: `6ecb09706140f8730b5385c08f1386c654c3c526`

## Load

- Requests: 8648
- Throughput: 192.11 req/s
- Hard error rate: 0.0000
- p50/p95/p99 latency: 8.57/20.90/29.08 ms

## GDA Overhead

- Services: 27
- Active edges median/max: 24/24
- Median density: 0.034188
- Sparse/dense logical Prometheus queries: 2/1404
- Query reduction: 702.0x
- GDA total p50/p95: 8.921/10.354 ms
- Graph-build p50/p95: 0.406/0.532 ms
- Peak Python memory p95: 0.025467 MiB

## Pod/Node Occupancy

- Worker nodes selected: 45
- Actual app pods: 27
- Ready app pods: 27
- Non-empty worker nodes: 22
- Occupancy ratio: 0.4889
- Evidence label: worker-pool/candidate-space evidence

## Claim Boundary

Use measured rows only for Algorithm 1 live benchmark overhead. Blocked rows document deployment or telemetry feasibility, not benchmark performance.
