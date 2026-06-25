# Standard Evaluation Summary: physical-social-scale-series-20260523T184422Z

Source run ledger: `experiments/runs/physical-social-scale-series-20260523T184422Z`

| Metric | Unit | scale10-kubernetes | scale10-policy1 | scale20-kubernetes | scale20-policy1 | scale30-kubernetes | scale30-policy1 | scale45-kubernetes | scale45-policy1 | scale5-kubernetes | scale5-policy1 | Source |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 80.681 | 29.414 | 76.885 | 63.387 | 28.910 | 67.602 | 73.426 | 70.180 | 21.146 | 17.569 | `processed/physical_social_metrics.json#p50_latency_ms` |
| `latency_p95_ms` | ms | 171.33 | 77.787 | 168.24 | 113.65 | 90.666 | 114.81 | 111.41 | 117.04 | 79.204 | 66.869 | `processed/physical_social_metrics.json#p95_latency_ms` |
| `latency_p99_ms` | ms | 178.69 | 81.180 | 172.94 | 153.76 | 92.175 | 159.64 | 114.50 | 168.31 | 82.427 | 72.046 | `processed/physical_social_metrics.json#p99_latency_ms` |
| `throughput_rps` | requests/s | 96.574 | 206.17 | 107.56 | 128.58 | 170.30 | 120.56 | 122.97 | 119.80 | 223.50 | 277.41 | `processed/physical_social_metrics.json#throughput_rps` |
| `sla_violations` | count | 8.0000 | 0.0000 | 9.0000 | 2.0000 | 0.0000 | 3.0000 | 1.0000 | 2.0000 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#sla_violations` |
| `sla_violation_rate` | ratio | 0.0889 | 0.0000 | 0.1000 | 0.0222 | 0.0000 | 0.0333 | 0.0111 | 0.0222 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#sla_violation_rate` |
| `scheduler_decision_time_ms` | ms | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#scheduler_decision_time_ms` |
| `gda_build_time_ms` | ms | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `processed/physical_social_metrics.json#gda_build_time_ms` |
| `ndm_injection_time_ms` | ms | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `migration_count` | count | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#migration_count` |
| `network_target_vs_measured_error` | unitless | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `processed/physical_social_metrics.json#network_target_vs_measured_error` |
| `placement_cost_reduction_pct` | percent | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.

Detailed distribution statistics, when raw samples are available, are written to `processed/detailed_statistics.csv` and include mean, median, p95, p99, standard deviation, IQR, 95% bootstrap mean interval, absolute delta, and percentage delta.
