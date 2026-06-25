# Standard Evaluation Summary: live-tc-social-scale45-20260603T074207Z

Source run ledger: `experiments/runs/live-tc-social-scale45-20260603T074207Z`

| Metric | Unit | kubernetes | policy1 | policy4 | Source |
| --- | --- | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 111.15 | 39.218 | 204.40 | `processed/social_live_tc_metrics.json#p50_latency_ms` |
| `latency_p95_ms` | ms | 416.80 | 91.381 | 671.53 | `processed/social_live_tc_metrics.json#p95_latency_ms` |
| `latency_p99_ms` | ms | 428.12 | 92.524 | 688.21 | `processed/social_live_tc_metrics.json#p99_latency_ms` |
| `throughput_rps` | requests/s | 39.003 | 168.98 | 19.872 | `processed/social_live_tc_metrics.json#throughput_rps` |
| `sla_violations` | count | 0.0000 | 0.0000 | 0.0000 | `processed/social_live_tc_metrics.json#errors` |
| `sla_violation_rate` | ratio | 0.0000 | 0.0000 | 0.0000 | `processed/social_live_tc_metrics.json#errors/requests` |
| `scheduler_decision_time_ms` | ms | n/a | n/a | n/a | not measured |
| `gda_build_time_ms` | ms | n/a | n/a | n/a | not measured |
| `ndm_injection_time_ms` | ms | n/a | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | n/a | n/a | not measured |
| `migration_count` | count | n/a | n/a | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | n/a | n/a | not measured |
| `placement_cost_reduction_pct` | percent | n/a | n/a | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.

Detailed distribution statistics, when raw samples are available, are written to `processed/detailed_statistics.csv` and include mean, median, p95, p99, standard deviation, IQR, 95% bootstrap mean interval, absolute delta, and percentage delta.
