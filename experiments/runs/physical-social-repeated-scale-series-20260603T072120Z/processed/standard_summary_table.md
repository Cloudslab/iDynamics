# Standard Evaluation Summary: physical-social-repeated-scale-series-20260603T072120Z

Source run ledger: `experiments/runs/physical-social-repeated-scale-series-20260603T072120Z`

| Scale | Policy | Reps | p50 ms | p95 ms | p99 ms | Throughput rps | SLA violations | SLA violation rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scale20 | kubernetes | 5 | 54.95 [32.88, 76.87] | 130.91 [94.72, 167.11] | 135.27 [98.80, 171.73] | 153.01 [107.46, 198.56] | 3.60 [1.00, 6.20] | 0.0400 [0.0111, 0.0689] |
| scale20 | policy1 | 5 | 42.27 [25.13, 59.41] | 104.95 [84.69, 130.81] | 121.20 [90.63, 151.77] | 164.98 [127.90, 202.05] | 1.60 [0.00, 4.00] | 0.0178 [0.0000, 0.0444] |
| scale30 | kubernetes | 5 | 39.61 [24.16, 57.68] | 101.62 [86.41, 123.69] | 109.46 [89.62, 137.25] | 165.96 [134.33, 195.03] | 1.00 [0.00, 2.60] | 0.0111 [0.0000, 0.0289] |
| scale30 | policy1 | 5 | 43.19 [28.43, 57.63] | 97.76 [82.51, 110.04] | 114.93 [93.19, 136.67] | 164.08 [132.70, 205.72] | 0.20 [0.00, 0.60] | 0.0022 [0.0000, 0.0067] |
| scale45 | kubernetes | 5 | 43.99 [20.72, 67.26] | 98.79 [47.12, 150.45] | 102.71 [49.12, 153.73] | 88.13 [41.48, 134.79] | 3.00 [0.00, 7.00] | 0.0333 [0.0000, 0.0778] |
| scale45 | policy1 | 5 | 44.64 [27.49, 61.80] | 272.37 [84.86, 621.15] | 301.92 [97.15, 662.12] | 142.77 [93.16, 197.97] | 2.60 [0.40, 5.40] | 0.0289 [0.0044, 0.0600] |

## Evidence Gate

Every value above is computed from the per-repetition raw request logs and pod snapshots archived in this run ledger. Percentage deltas must cite `processed/physical_social_policy_deltas.csv` and be interpreted with the bootstrap confidence intervals above.
