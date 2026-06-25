# live-tc-social-scale10-20260523T180124Z

Status: completed

## Purpose
Run a live destination-specific tc application experiment on Social Network-compatible traffic for Kubernetes baseline, Policy 1, and Policy 4 placement modes.

## Results
| Placement | Success | p50 ms | p95 ms | p99 ms | rps |
| --- | ---: | ---: | ---: | ---: | ---: |
| kubernetes | 60/60 | 175.37 | 526.46 | 541.66 | 26.14 |
| policy1 | 60/60 | 34.50 | 90.54 | 93.85 | 178.63 |
| policy4 | 60/60 | 177.21 | 607.51 | 622.59 | 22.28 |

## Side Effects
- Before tc: kubectl node check rc=0, DNS running mentions=2.
- After reset: kubectl node check rc=0, DNS running mentions=2.
- Qdisc snapshots are archived in env/qdisc_before, env/qdisc_after_apply, env/qdisc_before_reset, and env/qdisc_after_reset.

## Boundary
The tc filters target selected worker node IP destinations. On this Calico overlay cluster that is the practical live path for pod-to-pod traffic, but it can also delay other worker-to-worker overlay packets among the selected workers. The run therefore reports side-effect checks and avoids claims that non-experimental worker-to-worker overlay traffic is completely untouched.
