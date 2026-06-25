# Standard Evaluation Summary: moe-serving-scale10-20260523T183125Z

Source run ledger: `experiments/runs/moe-serving-scale10-20260523T183125Z`

| Metric | Unit | kubernetes-default | policy2 | policy3 | policy4 | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 27.995 | 25.939 | 25.953 | 26.014 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy2_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy3_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy4_latency_ms` |
| `latency_p95_ms` | ms | 29.441 | 27.380 | 27.010 | 27.311 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy2_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy3_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy4_latency_ms` |
| `latency_p99_ms` | ms | 29.793 | 27.991 | 27.316 | 27.387 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy2_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy3_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy4_latency_ms` |
| `throughput_rps` | requests/s | 60.000 | 60.000 | 60.000 | 60.000 | `raw/moe_expert_skew_timeseries.csv#step` |
| `sla_violations` | count | n/a | n/a | n/a | n/a | not measured |
| `sla_violation_rate` | ratio | n/a | n/a | n/a | n/a | not measured |
| `scheduler_decision_time_ms` | ms | n/a | n/a | n/a | n/a | not measured |
| `gda_build_time_ms` | ms | n/a | n/a | n/a | n/a | not measured |
| `ndm_injection_time_ms` | ms | n/a | n/a | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | n/a | n/a | n/a | not measured |
| `migration_count` | count | n/a | n/a | n/a | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | n/a | n/a | n/a | not measured |
| `placement_cost_reduction_pct` | percent | 0.0000 | 28.432 | 27.703 | 28.250 | `raw/moe_expert_skew_timeseries.csv#default_cost_reduction_pct`; `raw/moe_expert_skew_timeseries.csv#policy2_cost_reduction_pct`; `raw/moe_expert_skew_timeseries.csv#policy3_cost_reduction_pct`; `raw/moe_expert_skew_timeseries.csv#policy4_cost_reduction_pct` |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.
