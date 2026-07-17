# MoE Serving

MoE Serving is a repository-local, CPU-only microservice benchmark for
mixture-of-experts style routing. It models frontend, tokenizer, router,
expert, aggregator, and cache services with standard Python HTTP services and
bounded CPU work.

## Source And License

- Implementation: `benchmarks/moe-serving/app/server.py`
- License: repository package metadata (`MIT`)
- GPU required: no
- External model weights required: no

## Scripts

Run any script with `--help`.

```bash
benchmarks/moe-serving/scripts/fetch.sh
benchmarks/moe-serving/scripts/deploy.sh --namespace idyn-moe-serving
benchmarks/moe-serving/scripts/smoke.sh --namespace idyn-moe-serving
benchmarks/moe-serving/scripts/load.sh --namespace idyn-moe-serving
benchmarks/moe-serving/scripts/collect.sh --namespace idyn-moe-serving
benchmarks/moe-serving/scripts/cleanup.sh --namespace idyn-moe-serving
```

`deploy.sh` generates Kubernetes Deployment and Service manifests from the
local Python service and mounts the code through a ConfigMap. `reproduce.sh`
runs deploy, smoke, load, and collect in sequence. Set `IDYN_CLEANUP=1` to
delete the namespace afterward.

## Request Types

- `single_expert`
- `multi_expert_top2`
- `multi_expert_top4`
- `cache_hit`
- `cache_miss`
- `payload_small`
- `payload_large`
- `batch_small`
- `batch_large`

## Adapter Files

- `adapter/service_map.yaml`
- `adapter/workload_mix.yaml`
- `adapter/replica_profiles.yaml`
- `metadata.yaml`

## Known Limitations

- This benchmark models CPU-only routing and communication effects.
- It does not claim GPU scheduling, production LLM inference, or model-serving throughput.
- The service uses Python standard-library HTTP for portability, not optimized serving frameworks.
