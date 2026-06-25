# external-online-boutique-scale20-20260611T123228Z

Status: performance evidence

Namespace: `external-online-boutique-scale20-20260611t123228z`
Scale: `scale20`

Endpoint health: HTTP 200 in 906.07 ms

## Repeated Load

| Repeat | Requests | Throughput req/s | Error rate | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2970 | 66.00 | 0.0000 | 104.62 | 190.62 | 443.51 |
| 2 | 2867 | 63.71 | 0.0000 | 105.73 | 187.78 | 800.47 |
| 3 | 2896 | 64.36 | 0.0000 | 108.95 | 191.01 | 203.44 |

## GDA Call Graph

Reconstructed `11` workloads and `15` directed edges from Istio Prometheus telemetry.
