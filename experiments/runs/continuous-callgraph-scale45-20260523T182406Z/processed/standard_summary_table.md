# Standard Evaluation Summary: continuous-callgraph-scale45-20260523T182406Z

Source run ledger: `experiments/runs/continuous-callgraph-scale45-20260523T182406Z`

| Metric | Unit | workload-mixer | Source |
| --- | --- | ---: | --- |
| `latency_p50_ms` | ms | 103.85 | `raw/request_mix_timeseries.csv#latency_ms` |
| `latency_p95_ms` | ms | 145.43 | `raw/request_mix_timeseries.csv#latency_ms` |
| `latency_p99_ms` | ms | 155.77 | `raw/request_mix_timeseries.csv#latency_ms` |
| `throughput_rps` | requests/s | 180.00 | `raw/request_mix_timeseries.csv#qps_*` |
| `sla_violations` | count | n/a | not measured |
| `sla_violation_rate` | ratio | 0.0052 | `raw/request_mix_timeseries.csv#sla_violation_ratio` |
| `scheduler_decision_time_ms` | ms | n/a | not measured |
| `gda_build_time_ms` | ms | n/a | not measured |
| `ndm_injection_time_ms` | ms | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | not measured |
| `migration_count` | count | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | not measured |
| `placement_cost_reduction_pct` | percent | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.

Detailed distribution statistics, when raw samples are available, are written to `processed/detailed_statistics.csv` and include mean, median, p95, p99, standard deviation, IQR, 95% bootstrap mean interval, absolute delta, and percentage delta.
