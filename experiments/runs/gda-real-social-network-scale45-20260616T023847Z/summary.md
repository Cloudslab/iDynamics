# gda-real-social-network-scale45-20260616T023847Z

Status: telemetry_blocked
Benchmark: DeathStarBench Social Network
Namespace: `gda-real-social-network-scale45-20260616t023847z`
Scale: `scale45`

Source commit: `6ecb09706140f8730b5385c08f1386c654c3c526`

## Load

- Requests: 56014
- Throughput: 1244.70 req/s
- Hard error rate: 0.8689
- p50/p95/p99 latency: 9.89/78.50/88.23 ms

## GDA Overhead

- Services: 27
- Active edges median/max: 0/0
- Median density: 0.000000
- Sparse/dense logical Prometheus queries: 2/1404
- Query reduction: 702.0x
- GDA total p50/p95: 3.834/4.349 ms
- Graph-build p50/p95: 0.189/0.308 ms
- Peak Python memory p95: 0.011673 MiB

## Pod/Node Occupancy

- Worker nodes selected: 45
- Actual app pods: 28
- Ready app pods: 27
- Non-empty worker nodes: 26
- Occupancy ratio: 0.5778
- Evidence label: worker-pool/candidate-space evidence

## Blocker

telemetry produced too few active edges for social-network: {'samples': 7, 'service_count': 27, 'active_edges_median': 0.0, 'active_edges_max': 0.0, 'density_median': 0.0, 'sparse_query_count': 2, 'dense_logical_query_count': 1404, 'query_reduction_ratio_vs_dense': 702.0, 'prometheus_query_latency_p50_ms': 3.6472007632255554, 'prometheus_query_latency_p95_ms': 4.157952032983303, 'graph_build_wall_p50_ms': 0.18949713557958603, 'graph_build_wall_p95_ms': 0.3078412264585495, 'graph_build_cpu_p50_ms': 0.18085900000031074, 'graph_build_cpu_p95_ms': 0.2894630000014331, 'gda_total_wall_p50_ms': 3.834071569144726, 'gda_total_wall_p95_ms': 4.348930902779102, 'peak_python_memory_p95_mib': 0.0116729736328125, 'dense_local_pair_scan_wall_p95_ms': 0.06979098543524742, 'metric_sources': ['istio_requests_total_fallback']}

## Claim Boundary

Use measured rows only for Algorithm 1 live benchmark overhead. Blocked rows document deployment or telemetry feasibility, not benchmark performance.
