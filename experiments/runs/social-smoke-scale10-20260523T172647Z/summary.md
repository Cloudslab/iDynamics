# social-smoke-scale10-20260523T172647Z

Status: completed

## Benchmark
Self-contained DeathStarBench Social Network-compatible smoke deployment.

## Placement
- Scale: scale10
- Node selector: `idynamics.dev/scale10=true`
- Selected Ready workers: emu-worker-1, emu-worker-10, emu-worker-2, emu-worker-3, emu-worker-4, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9
- Control-plane node was not selected.

## Load
- Requests: 60
- Success: 60
- Errors: 0
- p50/p95/p99 latency: 39.60/99.95/102.72 ms
- Throughput: 144.81 rps

## Limitations
This smoke deployment validates reproducible Kubernetes placement, endpoint compatibility, workload generation, and log capture. It is not a full upstream DeathStarBench Social Network deployment with MongoDB, Redis, RabbitMQ, and OpenResty-Thrift.
