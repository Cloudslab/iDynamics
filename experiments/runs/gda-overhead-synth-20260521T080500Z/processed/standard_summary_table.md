# Standard Evaluation Summary: gda-overhead-synth-20260521T080500Z

Source run ledger: `experiments/runs/gda-overhead-synth-20260521T080500Z`

| Metric | Unit | dense-pair-scan | sparse-gda | Source |
| --- | --- | ---: | ---: | --- |
| `latency_p50_ms` | ms | n/a | n/a | not measured |
| `latency_p95_ms` | ms | n/a | n/a | not measured |
| `latency_p99_ms` | ms | n/a | n/a | not measured |
| `throughput_rps` | requests/s | n/a | n/a | not measured |
| `sla_violations` | count | n/a | n/a | not measured |
| `sla_violation_rate` | ratio | n/a | n/a | not measured |
| `scheduler_decision_time_ms` | ms | n/a | n/a | not measured |
| `gda_build_time_ms` | ms | 0.7396 | 0.5811 | `raw/gda_overhead_repetitions.csv#dense_seconds`; `raw/gda_overhead_repetitions.csv#sparse_seconds` |
| `ndm_injection_time_ms` | ms | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | n/a | not measured |
| `migration_count` | count | n/a | n/a | not measured |
| `network_target_vs_measured_error` | unitless | n/a | n/a | not measured |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.
