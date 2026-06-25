# Standard Evaluation Summary: mesh-overhead-20260523T165749Z

Source run ledger: `experiments/runs/mesh-overhead-20260523T165749Z`

| Metric | Unit | scale20-no-sidecar | scale20-sidecar | scale45-no-sidecar | scale45-sidecar | scale5-no-sidecar | scale5-sidecar | Source |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 0.8814 | 5.4413 | 1.2213 | 5.4931 | 1.0769 | 4.6363 | `processed/mesh_overhead_summary.json#p50_ms_mean` |
| `latency_p95_ms` | ms | 1.8755 | 6.9442 | 1.8804 | 7.0214 | 1.8247 | 6.1234 | `processed/mesh_overhead_summary.json#p95_ms_mean` |
| `latency_p99_ms` | ms | 2.1878 | 8.6306 | 2.4115 | 7.6130 | 2.3079 | 6.9711 | `processed/mesh_overhead_summary.json#p99_ms_mean` |
| `throughput_rps` | requests/s | 99.985 | 99.953 | 99.987 | 99.955 | 99.988 | 99.961 | `processed/mesh_overhead_summary.json#throughput_rps_mean` |
| `sla_violations` | count | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `sla_violation_rate` | ratio | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `scheduler_decision_time_ms` | ms | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `gda_build_time_ms` | ms | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `ndm_injection_time_ms` | ms | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | 0.0000 | 3.9169 | 0.0000 | 4.2993 | 0.0000 | 3.2652 | `processed/mesh_overhead_summary.json#istio_proxy_cpu_cores_mean` |
| `memory_overhead_mb` | MiB | 0.0000 | 70.026 | 0.0000 | 68.841 | 0.0000 | 66.888 | `processed/mesh_overhead_summary.json#istio_proxy_memory_mib_mean` |
| `migration_count` | count | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `placement_cost_reduction_pct` | percent | n/a | n/a | n/a | n/a | n/a | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.

Detailed distribution statistics, when raw samples are available, are written to `processed/detailed_statistics.csv` and include mean, median, p95, p99, standard deviation, IQR, 95% bootstrap mean interval, absolute delta, and percentage delta.
