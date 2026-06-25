# Standard Evaluation Summary: moe-serving-20260521T112045Z

Source run ledger: `experiments/runs/moe-serving-20260521T112045Z`

| Metric | Unit | idynamics-hot-path | kubernetes-default | Source |
| --- | --- | ---: | ---: | --- |
| `latency_p50_ms` | ms | 26.645 | 28.047 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#idynamics_latency_ms` |
| `latency_p95_ms` | ms | 28.268 | 29.441 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#idynamics_latency_ms` |
| `latency_p99_ms` | ms | 29.941 | 29.793 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#idynamics_latency_ms` |
| `throughput_rps` | requests/s | 48.000 | 48.000 | `raw/moe_expert_skew_timeseries.csv#step` |
| `sla_violations` | count | n/a | n/a | not measured |
| `sla_violation_rate` | ratio | n/a | n/a | not measured |
| `scheduler_decision_time_ms` | ms | n/a | n/a | not measured |
| `gda_build_time_ms` | ms | n/a | n/a | not measured |
| `ndm_injection_time_ms` | ms | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | n/a | not measured |
| `migration_count` | count | n/a | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.
