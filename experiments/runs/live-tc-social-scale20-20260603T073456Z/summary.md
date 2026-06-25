# live-tc-social-scale20-20260603T073456Z

Status: completed

## Purpose
Run a live destination-specific tc application experiment on Social Network-compatible traffic for Kubernetes baseline, Policy 1, and Policy 4 placement modes.

## Results
| Placement | Rep | Success | p50 ms | p95 ms | p99 ms | rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kubernetes | 1 | 60/60 | 126.62 | 495.51 | 512.46 | 29.29 |
| policy1 | 1 | 60/60 | 41.68 | 105.55 | 116.70 | 146.22 |
| policy4 | 1 | 60/60 | 302.47 | 772.42 | 782.95 | 15.89 |
| kubernetes | 2 | 60/60 | 238.09 | 699.46 | 705.76 | 18.28 |
| policy1 | 2 | 60/60 | 24.73 | 84.04 | 86.88 | 186.41 |
| policy4 | 2 | 60/60 | 220.69 | 617.28 | 625.75 | 20.42 |
| kubernetes | 3 | 60/60 | 122.32 | 396.43 | 413.86 | 33.71 |
| policy1 | 3 | 60/60 | 41.20 | 101.13 | 105.08 | 152.53 |
| policy4 | 3 | 60/60 | 107.06 | 381.82 | 393.79 | 36.27 |

## Aggregate
| Placement | Reps | Success | mean p50 ms | mean p95 ms | mean p99 ms | mean rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kubernetes | 3 | 180/180 | 162.34 | 530.47 | 544.03 | 27.09 |
| policy1 | 3 | 180/180 | 35.87 | 96.91 | 102.88 | 161.72 |
| policy4 | 3 | 180/180 | 210.07 | 590.51 | 600.83 | 24.19 |

## Side Effects
- Before tc: kubectl node check rc=0, DNS running mentions=2.
- After reset: kubectl node check rc=0, DNS running mentions=2.
- Qdisc snapshots are archived in env/qdisc_before, env/qdisc_after_apply, env/qdisc_before_reset, and env/qdisc_after_reset.
- The exact applied matrix is archived in raw/applied_tc_matrix.csv; the full burst-correlated trace is archived in raw/burst_correlated_trace.csv.

## Boundary
The tc filters target selected worker node IP destinations. On this Calico overlay cluster that is the practical live path for pod-to-pod traffic, but it can also delay other worker-to-worker overlay packets among the selected workers. The run therefore reports side-effect checks and avoids claims that non-experimental worker-to-worker overlay traffic is completely untouched.
