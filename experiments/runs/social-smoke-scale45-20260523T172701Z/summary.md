# social-smoke-scale45-20260523T172701Z

Status: completed

## Benchmark
Self-contained DeathStarBench Social Network-compatible smoke deployment.

## Placement
- Scale: scale45
- Node selector: `idynamics.dev/scale45=true`
- Selected Ready workers: emu-worker-1, emu-worker-10, emu-worker-11, emu-worker-12, emu-worker-13, emu-worker-14, emu-worker-15, emu-worker-16, emu-worker-17, emu-worker-18, emu-worker-19, emu-worker-2, emu-worker-20, emu-worker-21, emu-worker-22, emu-worker-23, emu-worker-24, emu-worker-25, emu-worker-26, emu-worker-27, emu-worker-28, emu-worker-29, emu-worker-3, emu-worker-30, emu-worker-31, emu-worker-32, emu-worker-33, emu-worker-34, emu-worker-35, emu-worker-36, emu-worker-37, emu-worker-38, emu-worker-39, emu-worker-4, emu-worker-40, emu-worker-41, emu-worker-42, emu-worker-43, emu-worker-44, emu-worker-45, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9
- Control-plane node was not selected.

## Load
- Requests: 60
- Success: 60
- Errors: 0
- p50/p95/p99 latency: 43.82/107.50/150.59 ms
- Throughput: 147.05 rps

## Limitations
This smoke deployment validates reproducible Kubernetes placement, endpoint compatibility, workload generation, and log capture. It is not a full upstream DeathStarBench Social Network deployment with MongoDB, Redis, RabbitMQ, and OpenResty-Thrift.
