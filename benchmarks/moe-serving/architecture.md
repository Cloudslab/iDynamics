# MoE Serving Architecture

The benchmark is a CPU-only microservice approximation of MoE serving:

```text
frontend -> tokenizer -> router -> expert-N -> aggregator -> cache
```

Every component is served by the same Python HTTP server with role-specific
behavior selected through `MOE_ROLE`.

## Components

- `frontend`: receives `/infer` requests, optionally checks cache, and forwards
  uncached requests to `tokenizer`.
- `tokenizer`: simulates tokenization delay and forwards token metadata.
- `router`: selects one or more experts from an expert-popularity vector and
  fans out to `expert-N` services.
- `expert-N`: simulates expert compute and returns a payload.
- `aggregator`: combines expert responses and writes the result to `cache`.
- `cache`: simple in-memory key/value service used to model hit and miss paths.

## APIs

Every service exposes:

- `GET /healthz`
- `GET /metrics`

Role-specific POST routes are:

- `frontend`: `/infer`
- `tokenizer`: `/tokenize`
- `router`: `/route`
- `expert-N`: `/infer`
- `aggregator`: `/aggregate`
- `cache`: `/get`, `/put`

## Kubernetes Shape

The manifest renderer creates one `Namespace`, one `Deployment` and one
`Service` for each fixed role, plus one `Deployment` and `Service` per expert.
For `--experts 6`, the service set is:

```text
frontend
tokenizer
router
aggregator
cache
expert-0
expert-1
expert-2
expert-3
expert-4
expert-5
```

The standard renderer expects a container image that includes
`examples/moe-serving/moe_service/server.py`. The physical runner can instead
mount the server through a ConfigMap and use `python:3.11-slim`.

## Placement Policies

- Kubernetes default: no MoE-aware placement preference.
- CGA / Policy 1: colocates hot-path actors and hot experts.
- Policy 2: emphasizes frontend/tokenizer/router/aggregator and hot-expert
  latency.
- Policy 3: emphasizes payload-heavy router/expert/aggregator edges.
- HDA / Policy 4: hybrid hot-path placement with cache separated when possible.

The renderer writes policy labels and preferred node affinity. The physical
runner also labels candidate nodes with `idynamics.io/placement-group` while a
policy is running, then removes those labels in cleanup.

## Workload Model

The load generator sends HTTP requests with:

- request type
- expert-popularity vector
- selected `top_k`
- payload size
- batch size
- compute delay
- cache key and cache hit intent

The request modes are defined in `adapter/workload_mix.yaml` and implemented by
`idynamics.workloads.moe`.

## Metrics

The service exports Prometheus text metrics:

- `moe_requests_total`
- `moe_request_latency_ms_sum`
- `moe_request_latency_ms_count`
- `moe_payload_bytes_total`
- `moe_expert_hits_total`
- `moe_cache_events_total`

The load generator records end-to-end request status and latency in CSV form.


## Result Boundary

The benchmark intentionally does not model GPU kernels, KV-cache placement,
tensor parallelism, model weights, or production LLM serving. It is a
microbenchmark for dynamic expert routing, payload movement, cache effects, and
iDynamics policy replay/placement behavior.
