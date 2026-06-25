# network-trace-calibrated-20260603T084310Z

Status: completed

## Purpose
Calibrate the burst-correlated iDynamics network trace generator against a small public RIPE Atlas built-in ping sample.

## Source
- Dataset: RIPE Atlas built-in IPv4 ping measurement 1001 toward k.root-servers.net.
- Window: 2026-06-02T07:43:10+00:00 to 2026-06-03T07:43:10+00:00.
- Requested probes: 1, 3, 6, 14, 18, 20, 25, 28, 30, 32, 37, 38.
- Contributing probes after parsing valid ping RTT averages: 1, 3, 6, 14, 18, 25, 28, 38.
- Terms recorded in `source_metadata.md`.

## Key Metrics
| Source | p50 ms | p95 ms | p99 ms | CV | Peak/median | Lag-1 autocorr. | Spatial corr. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RIPE Atlas sample | 22.626 | 75.715 | 79.646 | 1.864 | 115.999 | 0.066 | 0.001 |
| Fitted burst generator | 24.504 | 64.958 | 83.998 | 0.520 | 4.551 | 0.859 | -0.002 |

## Selected Generator Parameters
- temporal_correlation: 0.35
- spatial_correlation: 0.0
- burst_probability: 0.08
- base_latency_ms: 14.706684525000002

