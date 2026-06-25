# external-hotel-scale10-20260523T172949Z

Status: completed

## Benchmark
DeathStarBench Hotel Reservation upstream Kubernetes manifests.

## Placement
- Scale: scale10
- Node selector patched onto deployments: `idynamics.dev/scale10=true`
- Selected Ready workers: emu-worker-1, emu-worker-10, emu-worker-2, emu-worker-3, emu-worker-4, emu-worker-5, emu-worker-6, emu-worker-7, emu-worker-8, emu-worker-9

## Smoke Result
- Requests: 10
- Success: 10
- Errors: 0
- p95 latency: 38.30 ms
