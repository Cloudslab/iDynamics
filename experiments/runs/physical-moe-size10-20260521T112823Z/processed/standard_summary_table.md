# Standard Evaluation Summary: physical-moe-size10-20260521T112823Z

Source run ledger: `experiments/runs/physical-moe-size10-20260521T112823Z`

| Metric | Unit | idynamics-policy1-callgraph-aware | kubernetes-default | Source |
| --- | --- | ---: | ---: | --- |
| `latency_p50_ms` | ms | 38.003 | 39.638 | `processed/physical_moe_metrics.json#p50_latency_ms` |
| `latency_p95_ms` | ms | 40.836 | 42.091 | `processed/physical_moe_metrics.json#p95_latency_ms` |
| `latency_p99_ms` | ms | 42.920 | 44.101 | `processed/physical_moe_metrics.json#p99_latency_ms` |
| `throughput_rps` | requests/s | 7.9111 | 7.9141 | `processed/physical_moe_metrics.json#throughput_rps` |
| `sla_violations` | count | 0.0000 | 0.0000 | `processed/physical_moe_metrics.json#sla_violations` |
| `sla_violation_rate` | ratio | 0.0000 | 0.0000 | `processed/physical_moe_metrics.json#sla_violations/requests` |
| `scheduler_decision_time_ms` | ms | 12491.49 | 21295.99 | `processed/physical_moe_metrics.json#scheduler_ready_s` |
| `gda_build_time_ms` | ms | 0.0070 | 0.0054 | `processed/physical_moe_metrics.json#gda_build_time_ms` |
| `ndm_injection_time_ms` | ms | n/a | n/a | not measured |
| `cpu_overhead_pct` | percent | n/a | n/a | not measured |
| `memory_overhead_mb` | MiB | n/a | n/a | not measured |
| `migration_count` | count | 11.000 | 0.0000 | `processed/physical_moe_metrics.json#migration_count` |
| `network_target_vs_measured_error` | unitless | n/a | n/a | `processed/physical_moe_metrics.json#network_target_vs_measured_error` |

## Evidence Gate

Every value above is read from `raw/` or `processed/` data inside the named run ledger. Values marked `n/a` were not emitted by this run type and must not be used as paper claims.
