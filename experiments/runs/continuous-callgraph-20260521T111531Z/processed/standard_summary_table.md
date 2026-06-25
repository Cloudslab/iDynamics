# Standard Evaluation Summary: continuous-callgraph-20260521T111531Z

Source run ledger: `experiments/runs/continuous-callgraph-20260521T111531Z`

| Metric | Unit | workload-mixer | Source |
| --- | --- | ---: | --- |
| `latency_p50_ms` | ms | 106.98 | `raw/request_mix_timeseries.csv#latency_ms` |
| `latency_p95_ms` | ms | 120.52 | `raw/request_mix_timeseries.csv#latency_ms` |
| `latency_p99_ms` | ms | 123.49 | `raw/request_mix_timeseries.csv#latency_ms` |
| `throughput_rps` | requests/s | 90.000 | `raw/request_mix_timeseries.csv#qps_*` |
| `sla_violations` | count | n/a | not measured |
| `sla_violation_rate` | ratio | 0.0000 | `raw/request_mix_timeseries.csv#sla_violation_ratio` |
| `scheduler_decision_time_ms` | ms | n/a | not measured |
| `gda_build_time_ms` | ms | n/a | not measured |
| `ndm_injection_time_ms` | ms | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | not measured |
| `migration_count` | count | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.
