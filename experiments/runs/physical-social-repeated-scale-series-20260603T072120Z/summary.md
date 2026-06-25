# physical-social-repeated-scale-series-20260603T072120Z

Status: completed

## Scope
Worker-only Social Network-compatible physical scale run comparing Kubernetes baseline and Policy 1 static placement.

Safe run setting: 5 repetitions per scale/policy, 90 requests per repetition, concurrency 8, SLA threshold 150 ms.

## Aggregate Results
| Scale | Policy | Reps | Success mean | p50 ms mean [95% CI] | p95 ms mean [95% CI] | p99 ms mean [95% CI] | Throughput rps mean [95% CI] | SLA viol. mean [95% CI] | Sched. ms mean [95% CI] | Ready ms mean [95% CI] |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scale20 | kubernetes | 5 | 90.0 | 54.95 [32.88, 76.87] | 130.91 [94.72, 167.11] | 135.27 [98.80, 171.73] | 153.01 [107.46, 198.56] | 3.60 [1.00, 6.20] | 0 [0, 0] | 6597 [5232, 8067] |
| scale20 | policy1 | 5 | 90.0 | 42.27 [25.13, 59.41] | 104.95 [84.69, 130.81] | 121.20 [90.63, 151.77] | 164.98 [127.90, 202.05] | 1.60 [0.00, 4.00] | 0 [0, 0] | 6908 [5499, 8318] |
| scale30 | kubernetes | 5 | 90.0 | 39.61 [24.16, 57.68] | 101.62 [86.41, 123.69] | 109.46 [89.62, 137.25] | 165.96 [134.33, 195.03] | 1.00 [0.00, 2.60] | 0 [0, 0] | 4604 [4327, 4877] |
| scale30 | policy1 | 5 | 90.0 | 43.19 [28.43, 57.63] | 97.76 [82.51, 110.04] | 114.93 [93.19, 136.67] | 164.08 [132.70, 205.72] | 0.20 [0.00, 0.60] | 0 [0, 0] | 5439 [4361, 6589] |
| scale45 | kubernetes | 5 | 87.4 | 43.99 [20.72, 67.26] | 98.79 [47.12, 150.45] | 102.71 [49.12, 153.73] | 88.13 [41.48, 134.79] | 3.00 [0.00, 7.00] | 0 [0, 0] | 5401 [4543, 6475] |
| scale45 | policy1 | 5 | 90.0 | 44.64 [27.49, 61.80] | 272.37 [84.86, 621.15] | 301.92 [97.15, 662.12] | 142.77 [93.16, 197.97] | 2.60 [0.40, 5.40] | 0 [0, 0] | 4936 [4140, 5763] |

## Policy 1 Deltas
Percentage deltas are computed from repetition means. They are reported with the aggregate table above so no improvement claim is used without repetition support.

| Scale | p95 Policy 1 delta vs Kubernetes | Throughput Policy 1 delta vs Kubernetes | SLA violation-rate delta |
| --- | ---: | ---: | ---: |
| scale20 | -19.83% | 7.82% | -0.0222 |
| scale30 | -3.79% | -1.13% | -0.0089 |
| scale45 | 175.72% | 61.99% | -0.0044 |

## Raw Repetition Results
Per-repetition metrics are in `processed/physical_social_metrics.csv` and raw request logs are in `raw/*_repXX_loadgen.csv` for 30 completed scale/policy repetitions.

## Resource Collection
Pod specs, pod placement, node capacities, events, and services are archived under `raw/` and `env/`. Observed CPU/memory utilization was requested through `kubectl top`, but the Metrics API was unavailable on this cluster; the stderr is archived in `env/metrics_api_top_nodes.txt.err`.

## Boundaries
This is a short smoke-scale physical run for reviewer-facing scale evidence. It is not a full DeathStarBench Social Network deployment and does not apply live tc impairment.
