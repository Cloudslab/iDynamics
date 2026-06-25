# moe-serving-scale20-20260523T183126Z

Status: completed

## Purpose
Evaluate application generality with a MoE-style serving microbenchmark and compare default, policy2, policy3, policy4 under time-varying expert skew.

## Real Benchmark Inspection
Status: not_available_locally

No local DeathStarBench Hotel/Media or TrainTicket checkout/manifests were found under /home/ubuntu during this run; the stable MoE microbenchmark path was used.

## Result
- Added/rendered containerized MoE services with 8 experts.
- Generated Kubernetes manifests for default, policy2, policy3, policy4 in `raw/`.
- Simulated 60 skew intervals with 80 requests per interval.
- Best mean cost reduction relative to default was 46.75%.
- Best mean modeled latency was 24.23 ms.

## Limitations
This is a CPU-only microbenchmark/control-plane placement comparison unless `live_k8s` is true. It supports MoE-style dynamic expert-traffic modeling, not GPU-aware scheduling.
