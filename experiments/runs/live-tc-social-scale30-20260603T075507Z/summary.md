# live-tc-social-scale30-20260603T075507Z

Status: completed

## Purpose
Run a live destination-specific tc application experiment on Social Network-compatible traffic for Kubernetes baseline, Policy 1, and Policy 4 placement modes.

## Results
| Placement | Rep | Success | p50 ms | p95 ms | p99 ms | rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kubernetes | 1 | 60/60 | 183.67 | 474.77 | 479.23 | 26.54 |
| policy1 | 1 | 60/60 | 59.38 | 109.78 | 150.84 | 127.69 |
| policy4 | 1 | 60/60 | 220.22 | 677.24 | 1219.15 | 19.25 |
| kubernetes | 2 | 60/60 | 222.83 | 505.22 | 507.64 | 24.66 |
| policy1 | 2 | 60/60 | 71.87 | 166.85 | 169.99 | 108.50 |
| policy4 | 2 | 60/60 | 157.41 | 466.71 | 477.29 | 27.70 |
| kubernetes | 3 | 60/60 | 173.07 | 418.06 | 423.93 | 28.35 |
| policy1 | 3 | 60/60 | 55.44 | 110.21 | 158.90 | 131.71 |
| policy4 | 3 | 60/60 | 191.78 | 581.99 | 592.77 | 22.93 |

## Aggregate
| Placement | Reps | Success | mean p50 ms | mean p95 ms | mean p99 ms | mean rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kubernetes | 3 | 180/180 | 193.19 | 466.02 | 470.27 | 26.52 |
| policy1 | 3 | 180/180 | 62.23 | 128.95 | 159.91 | 122.64 |
| policy4 | 3 | 180/180 | 189.80 | 575.31 | 763.07 | 23.30 |

## Side Effects
- Before tc: kubectl node check rc=0, DNS running mentions=2.
- After reset: kubectl node check rc=0, DNS running mentions=2.
- Qdisc snapshots are archived in env/qdisc_before, env/qdisc_after_apply, env/qdisc_before_reset, and env/qdisc_after_reset.
- The exact applied matrix is archived in raw/applied_tc_matrix.csv; the full burst-correlated trace is archived in raw/burst_correlated_trace.csv.

## Boundary
The tc filters target selected worker node IP destinations. On this Calico overlay cluster that is the practical live path for pod-to-pod traffic, but it can also delay other worker-to-worker overlay packets among the selected workers. The run therefore reports side-effect checks and avoids claims that non-experimental worker-to-worker overlay traffic is completely untouched.
