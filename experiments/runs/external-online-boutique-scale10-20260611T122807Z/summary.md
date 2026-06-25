# external-online-boutique-scale10-20260611T122807Z

Status: performance evidence

Namespace: `external-online-boutique-scale10-20260611t122807z`
Scale: `scale10`

Endpoint health: HTTP 200 in 32.55 ms

## Repeated Load

| Repeat | Requests | Throughput req/s | Error rate | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2817 | 62.60 | 0.0000 | 107.31 | 191.09 | 692.83 |
| 2 | 2900 | 64.44 | 0.0000 | 105.48 | 183.69 | 862.71 |
| 3 | 3070 | 68.22 | 0.0000 | 107.04 | 181.28 | 191.63 |

## GDA Call Graph

Reconstructed `11` workloads and `15` directed edges from Istio Prometheus telemetry.
