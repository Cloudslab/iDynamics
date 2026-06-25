# Standard Evaluation Summary: physical-social-scale-series-20260523T183735Z

Source run ledger: `experiments/runs/physical-social-scale-series-20260523T183735Z`

| Metric | Unit | scale10-kubernetes | scale10-policy1 | scale20-kubernetes | scale20-policy1 | scale30-kubernetes | scale30-policy1 | scale45-kubernetes | scale45-policy1 | scale5-kubernetes | scale5-policy1 | Source |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 21.173 | 40.264 | 66.804 | 72.621 | 41.680 | 74.293 | 74.042 | 59.792 | 33.362 | 36.773 | `processed/physical_social_metrics.json#p50_latency_ms` |
| `latency_p95_ms` | ms | 80.292 | 93.044 | 119.17 | 123.63 | 94.031 | 161.07 | 1047.19 | 113.48 | 95.958 | 85.955 | `processed/physical_social_metrics.json#p95_latency_ms` |
| `latency_p99_ms` | ms | 83.596 | 95.676 | 159.43 | 163.66 | 94.667 | 172.18 | 1051.90 | 117.52 | 99.830 | 96.108 | `processed/physical_social_metrics.json#p99_latency_ms` |
| `throughput_rps` | requests/s | 197.63 | 175.92 | 120.67 | 106.74 | 167.22 | 103.89 | 52.905 | 130.80 | 152.84 | 188.35 | `processed/physical_social_metrics.json#throughput_rps` |
| `sla_violations` | count | 0.0000 | 0.0000 | 4.0000 | 3.0000 | 0.0000 | 5.0000 | 9.0000 | 1.0000 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#sla_violations` |
| `sla_violation_rate` | ratio | 0.0000 | 0.0000 | 0.0444 | 0.0333 | 0.0000 | 0.0556 | 0.1000 | 0.0111 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#sla_violation_rate` |
| `scheduler_decision_time_ms` | ms | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#scheduler_decision_time_ms` |
| `gda_build_time_ms` | ms | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `processed/physical_social_metrics.json#gda_build_time_ms` |
| `ndm_injection_time_ms` |  | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |
| `migration_count` | count | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `processed/physical_social_metrics.json#migration_count` |
| `network_target_vs_measured_error` | unitless | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `processed/physical_social_metrics.json#network_target_vs_measured_error` |
| `placement_cost_reduction_pct` |  | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.
