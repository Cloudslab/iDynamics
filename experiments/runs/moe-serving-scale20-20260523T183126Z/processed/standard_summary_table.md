# Standard Evaluation Summary: moe-serving-scale20-20260523T183126Z

Source run ledger: `experiments/runs/moe-serving-scale20-20260523T183126Z`

| Metric | Unit | kubernetes-default | policy2 | policy3 | policy4 | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `latency_p50_ms` | ms | 27.995 | 24.391 | 24.107 | 24.392 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy2_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy3_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy4_latency_ms` |
| `latency_p95_ms` | ms | 29.441 | 25.904 | 25.684 | 25.884 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy2_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy3_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy4_latency_ms` |
| `latency_p99_ms` | ms | 29.793 | 26.265 | 25.820 | 26.249 | `raw/moe_expert_skew_timeseries.csv#default_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy2_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy3_latency_ms`; `raw/moe_expert_skew_timeseries.csv#policy4_latency_ms` |
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
| `placement_cost_reduction_pct` | percent | 0.0000 | 49.597 | 49.076 | 49.466 | `raw/moe_expert_skew_timeseries.csv#default_cost_reduction_pct`; `raw/moe_expert_skew_timeseries.csv#policy2_cost_reduction_pct`; `raw/moe_expert_skew_timeseries.csv#policy3_cost_reduction_pct`; `raw/moe_expert_skew_timeseries.csv#policy4_cost_reduction_pct` |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.
