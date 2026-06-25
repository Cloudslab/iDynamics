# Standard Evaluation Summary: live-tc-social-scale20-20260603T073456Z

Source run ledger: `experiments/runs/live-tc-social-scale20-20260603T073456Z`

| Metric | Unit | kubernetes | policy1 | policy4 | Source |
| --- | --- | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 122.32 | 41.200 | 107.06 | `processed/social_live_tc_metrics.json#p50_latency_ms` |
| `latency_p95_ms` | ms | 396.43 | 101.13 | 381.82 | `processed/social_live_tc_metrics.json#p95_latency_ms` |
| `latency_p99_ms` | ms | 413.86 | 105.08 | 393.79 | `processed/social_live_tc_metrics.json#p99_latency_ms` |
| `throughput_rps` | requests/s | 33.713 | 152.53 | 36.269 | `processed/social_live_tc_metrics.json#throughput_rps` |
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
