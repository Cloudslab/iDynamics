# Standard Evaluation Summary: gda-scalability-synth-large-clean-20260616T030405Z

Source run ledger: `experiments/runs/gda-scalability-synth-large-clean-20260616T030405Z`

| Metric | Unit | dense-pairwise | sparse-aggregate | Source |
| --- | --- | ---: | ---: | --- |
| `latency_p50_ms` | ms | n/a | n/a | not measured |
| `latency_p95_ms` | ms | n/a | n/a | not measured |
| `latency_p99_ms` | ms | n/a | n/a | not measured |
| `throughput_rps` | requests/s | n/a | n/a | not measured |
| `sla_violations` | count | n/a | n/a | not measured |
| `sla_violation_rate` | ratio | n/a | n/a | not measured |
| `scheduler_decision_time_ms` | ms | 5.8534 | 30.536 | `raw/gda_overhead_repetitions.csv#graph_build_cpu_ms` |
| `gda_build_time_ms` | ms | 5.8569 | 30.542 | `raw/gda_overhead_repetitions.csv#graph_build_wall_ms` |
| `ndm_injection_time_ms` | ms | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | 0.0002 | 2.3647 | `raw/gda_overhead_repetitions.csv#peak_python_memory_mib` |
| `migration_count` | count | n/a | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | n/a | not measured |
| `placement_cost_reduction_pct` | percent | n/a | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.

Detailed distribution statistics, when raw samples are available, are written to `processed/detailed_statistics.csv` and include mean, median, p95, p99, standard deviation, IQR, 95% bootstrap mean interval, absolute delta, and percentage delta.
