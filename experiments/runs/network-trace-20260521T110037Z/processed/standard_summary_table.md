# Standard Evaluation Summary: network-trace-20260521T110037Z

Source run ledger: `experiments/runs/network-trace-20260521T110037Z`

| Metric | Unit | burst_correlated | csv_replay | synthetic_distance_random | Source |
| --- | --- | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 18.591 | 18.591 | 14.018 | `processed/network_trace_metrics.json#latency_ms.p50` |
| `latency_p95_ms` | ms | 45.117 | 45.117 | 42.828 | `processed/network_trace_metrics.json#latency_ms.p95` |
| `latency_p99_ms` | ms | 63.626 | 63.626 | 58.833 | `processed/network_trace_metrics.json#latency_ms.p99` |
| `throughput_rps` | requests/s | n/a | n/a | n/a | not measured |
| `sla_violations` | count | n/a | n/a | n/a | not measured |
| `sla_violation_rate` | ratio | n/a | n/a | n/a | not measured |
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
