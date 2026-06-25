# live-tc-social-scale45-20260603T074207Z

Status: completed

## Purpose
Run a live destination-specific tc application experiment on Social Network-compatible traffic for Kubernetes baseline, Policy 1, and Policy 4 placement modes.

## Results
| Placement | Rep | Success | p50 ms | p95 ms | p99 ms | rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kubernetes | 1 | 60/60 | 184.50 | 537.33 | 552.71 | 23.72 |
| policy1 | 1 | 60/60 | 19.94 | 73.19 | 74.78 | 221.31 |
| policy4 | 1 | 60/60 | 164.17 | 519.43 | 537.73 | 26.36 |
| kubernetes | 2 | 60/60 | 146.96 | 564.55 | 573.57 | 24.89 |
| policy1 | 2 | 60/60 | 40.31 | 87.28 | 90.43 | 174.85 |
| policy4 | 2 | 60/60 | 213.62 | 557.04 | 565.15 | 23.00 |
| kubernetes | 3 | 60/60 | 111.15 | 416.80 | 428.12 | 39.00 |
| policy1 | 3 | 60/60 | 39.22 | 91.38 | 92.52 | 168.98 |
| policy4 | 3 | 60/60 | 204.40 | 671.53 | 688.21 | 19.87 |

## Aggregate
| Placement | Reps | Success | mean p50 ms | mean p95 ms | mean p99 ms | mean rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kubernetes | 3 | 180/180 | 147.54 | 506.23 | 518.14 | 29.20 |
| policy1 | 3 | 180/180 | 33.16 | 83.95 | 85.91 | 188.38 |
| policy4 | 3 | 180/180 | 194.06 | 582.67 | 597.03 | 23.08 |

## Side Effects
- Before tc: kubectl node check rc=0, DNS running mentions=2.
- After reset: kubectl node check rc=0, DNS running mentions=2.
- Qdisc snapshots are archived in env/qdisc_before, env/qdisc_after_apply, env/qdisc_before_reset, and env/qdisc_after_reset.
- The exact applied matrix is archived in raw/applied_tc_matrix.csv; the full burst-correlated trace is archived in raw/burst_correlated_trace.csv.

## Boundary
The tc filters target selected worker node IP destinations. On this Calico overlay cluster that is the practical live path for pod-to-pod traffic, but it can also delay other worker-to-worker overlay packets among the selected workers. The run therefore reports side-effect checks and avoids claims that non-experimental worker-to-worker overlay traffic is completely untouched.
