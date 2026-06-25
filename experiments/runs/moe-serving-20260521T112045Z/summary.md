# moe-serving-20260521T112045Z

Status: completed

## Purpose
Evaluate application generality with a MoE-style serving microbenchmark and compare default Kubernetes-style placement with iDynamics hot-path placement under time-varying expert skew.

## Real Benchmark Inspection
Status: not_available_locally

No local DeathStarBench Hotel/Media or TrainTicket checkout/manifests were found under /home/ubuntu during this run; the stable MoE microbenchmark path was used.

## Result
- Added/rendered containerized MoE services with 6 experts.
- Generated default and iDynamics Kubernetes manifests in `raw/`.
- Simulated 48 skew intervals with 60 requests per interval.
- Mean traffic-weighted placement cost changed from 228465.72 to 195562.73.
- Mean modeled latency changed from 27.91 ms to 26.69 ms.

