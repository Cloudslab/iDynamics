# MoE Serving Microbenchmark

This benchmark models dynamic expert traffic for a lightweight mixture-of-experts
serving pipeline:

```text
frontend -> tokenizer -> router/gate -> expert-0..expert-k -> aggregator -> cache/state
```

It is intentionally CPU-only. It evaluates whether iDynamics can observe and
reason about MoE-style shifting expert traffic; it does not claim GPU-aware
scheduling.

## Components

- `moe_service/server.py`: one container image with role-specific behavior.
- `k8s/render_manifests.py`: renders Kubernetes manifests for a configurable
  number of experts, worker node-pool selection, and Policy 2/3/4 placement
  hints.
- `workload/generate_load.py`: HTTP workload generator with configurable expert
  popularity, skew mode, compute delay, payload size, experts per request, and
  cache-hit ratio.

## Local Smoke and Tests

```bash
python3 examples/moe-serving/workload/generate_load.py \
  --dry-run \
  --requests 20 \
  --skew-mode phase_shift

python3 examples/moe-serving/workload/generate_load.py \
  --dry-run \
  --requests 20 \
  --skew-mode markov

pytest -q tests/test_moe_serving_benchmark.py
```

The workload CSV records request id, status, latency, selected experts, hot
expert, expert popularity vector, cache key, and error text. The JSON summary
prints request count, status counts, p50/p95/p99 latency, throughput, and SLA
violations.

## Render Kubernetes Manifests

```bash
python3 examples/moe-serving/k8s/render_manifests.py \
  --experts 6 \
  --policy default \
  --output /tmp/moe-default.yaml

python3 examples/moe-serving/k8s/render_manifests.py \
  --experts 6 \
  --policy hda \
  --hot-experts 0,1 \
  --cache-hit-ratio 0.30 \
  --node-pool-label idynamics.dev/scale45=true \
  --output /tmp/moe-policy4-scale45.yaml
```

Build and push an image, then set `MOE_IMAGE` when rendering or running:

```bash
docker build -t registry.example/moe-serving:latest examples/moe-serving
MOE_IMAGE=registry.example/moe-serving:latest \
  benchmarks/moe-serving/scripts/deploy.sh
```

The default experiment target is a synthetic/control-plane run that archives a
run ledger and compares default Kubernetes-style spreading against Policy 2,
Policy 3, and Policy 4 control-plane placement models. Use
`IDYN_LIVE_PHYSICAL=1 benchmarks/moe-serving/scripts/reproduce.sh` only when
you want to mutate a live Kubernetes cluster.

## Live Kubernetes Reproduction

The physical runner uses `python:3.11-slim` plus a ConfigMap-mounted server by
default, so it can run without a custom registry image. It creates a full run
ledger under `experiments/runs/<run_id>/`, applies one policy namespace at a
time, runs load through a local port-forward, records pod placement and planner
outputs, and deletes namespaces and temporary node labels in `finally` cleanup.

```bash
MOE_SCALE=scale10 \
MOE_SKEWS="phase_shift markov" \
MOE_REQUESTS=120 \
MOE_QPS=10 \
examples/moe-serving/scripts/reproduce.sh
```

Run the requested campaign explicitly:

```bash
for scale in scale10 scale20 scale45; do
  MOE_SCALE="$scale" MOE_SKEWS="phase_shift markov" \
    examples/moe-serving/scripts/reproduce.sh
done
```

Each live run compares:

- Kubernetes default placement
- CGA
- HDA
- Policy 2 critical-path latency placement
- Policy 3 bandwidth/payload-aware placement

Collected evidence includes expert popularity, call-graph hotspots, p50/p95/p99,
throughput, SLA violations, pod placement decisions, migration count, objective
cost, and policy decision time. The runner does not apply `tc`; any optional
network impairment must use the repository qdisc snapshot/reset scripts first.

## Metrics Endpoints

Every service exposes:

- `GET /healthz`
- `GET /metrics` in Prometheus text format
- role-specific `POST` routes such as `/infer`, `/tokenize`, `/route`,
  `/aggregate`, `/get`, and `/put`

Important metric names are `moe_requests_total`,
`moe_request_latency_ms_sum`, `moe_request_latency_ms_count`,
`moe_payload_bytes_total`, `moe_expert_hits_total`, and
`moe_cache_events_total`.

## Claim Boundary

This benchmark is a CPU-only microservice benchmark for MoE-style routing,
expert skew, fan-out/fan-in payload movement, and cache effects. It does not
claim GPU-aware scheduling or production LLM-serving behavior.
