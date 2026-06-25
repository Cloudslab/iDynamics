# Mesh Overhead Benchmark: `mesh-overhead-20260523T165749Z`

- Fortio image: `fortio/fortio:1.69.3`
- Load: 100.0 qps, 16 connections, 15s, payload 1024 bytes.
- Repetitions requested: 5 per scale/condition.
- Scales requested: scale5, scale20, scale45.
- Resource metrics source: Prometheus cAdvisor (`kubectl top` was unavailable).

| Scale | Condition | Valid reps | Throughput rps mean | p50 ms mean | p95 ms mean | p99 ms mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| scale20 | no-sidecar | 5 | 99.985 | 0.881 | 1.876 | 2.188 |
| scale20 | sidecar | 5 | 99.953 | 5.441 | 6.944 | 8.631 |
| scale45 | no-sidecar | 5 | 99.987 | 1.221 | 1.880 | 2.411 |
| scale45 | sidecar | 5 | 99.955 | 5.493 | 7.021 | 7.613 |
| scale5 | no-sidecar | 5 | 99.988 | 1.077 | 1.825 | 2.308 |
| scale5 | sidecar | 5 | 99.961 | 4.636 | 6.123 | 6.971 |

## Claim Boundary

This run supports only the measured in-cluster Fortio two-service comparison under the recorded Kubernetes, Istio, Prometheus, CRI-O, and node-placement conditions. It does not by itself quantify every iDynamics application path.
