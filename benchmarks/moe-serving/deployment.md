# Deployment Guide

This guide describes the two supported reproduction paths.

## 1. Replay/Control-Plane Run

Replay mode is the easiest way to reproduce the benchmark logic. It does not
apply Kubernetes manifests and does not require a live cluster.

```bash
cd /home/ubuntu/iDynamics

IDYN_STAGE=single \
IDYN_SCALE=scale20 \
IDYN_REPLICA_PROFILE=replica3 \
IDYN_MODE=markov \
IDYN_STEPS=200 \
  benchmarks/moe-serving/scripts/reproduce.sh
```

The script creates a ledger under `experiments/runs/` and runs
`scripts/experiments/run_moe_longmix_replica.py`, which then calls
`scripts/experiments/continuous_callgraph.py`.

Run the full Stage A/B/C/D replay campaign:

```bash
IDYN_STAGE=all benchmarks/moe-serving/scripts/reproduce.sh
```

Useful replay variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `IDYN_STAGE` | `single` | `single`, `A`, `B`, `C`, `D`, or `all` |
| `IDYN_SCALE` | `scale20` | Logical worker pool label for evidence metadata |
| `IDYN_REPLICA_PROFILE` | `replica3` | `replica1`, `replica3`, or `replica5` |
| `IDYN_MODE` | `sinusoidal` | Long-mix mode |
| `IDYN_STEPS` | `200` | Number of snapshots |
| `IDYN_TOTAL_QPS` | `90` | Aggregate request rate used in replay |
| `IDYN_EXPERTS` | `6` | Number of expert services |
| `IDYN_RUN_ID` | generated | Optional fixed run id |

## 2. Live Single-Policy Kubernetes Deployment

Use this path when you want to render and apply one concrete Kubernetes
deployment.

First build and publish an image that contains the MoE server:

```bash
MOE_IMAGE=registry.example.com/idynamics/moe-serving:latest \
IDYN_PUSH_IMAGE=1 \
  benchmarks/moe-serving/scripts/build_image.sh
```

Label the target worker pool. The deployment scripts select nodes using
`idynamics.dev/<scale>=true`.

```bash
kubectl label node <worker-1> idynamics.dev/scale10=true --overwrite
kubectl label node <worker-2> idynamics.dev/scale10=true --overwrite
```

Render only, for inspection:

```bash
MOE_IMAGE=registry.example.com/idynamics/moe-serving:latest \
IDYN_SCALE=scale10 \
IDYN_POLICY=policy2 \
IDYN_MANIFEST=/tmp/idyn-moe-policy2.yaml \
  benchmarks/moe-serving/scripts/render.sh
```

Apply and wait for rollout:

```bash
MOE_IMAGE=registry.example.com/idynamics/moe-serving:latest \
IDYN_SCALE=scale10 \
IDYN_POLICY=policy2 \
  benchmarks/moe-serving/scripts/deploy.sh
```

Smoke test, run load, and collect metrics:

```bash
benchmarks/moe-serving/scripts/smoke.sh

IDYN_REQUESTS=120 \
IDYN_QPS=10 \
IDYN_SKEW_MODE=sinusoidal \
IDYN_OUTPUT=/tmp/idyn-moe-load.csv \
  benchmarks/moe-serving/scripts/run_load.sh

IDYN_METRICS_DIR=/tmp/idyn-moe-serving-metrics \
  benchmarks/moe-serving/scripts/collect_metrics.sh
```

Cleanup:

```bash
benchmarks/moe-serving/scripts/cleanup.sh
```

Useful live deployment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `IDYN_NAMESPACE` | `idyn-moe-serving` | Kubernetes namespace |
| `IDYN_SCALE` | `scale10` | Builds the default node selector label |
| `IDYN_NODE_POOL_LABEL` | `idynamics.dev/$IDYN_SCALE=true` | Override or blank out the node selector |
| `IDYN_POLICY` | `default` | `default`, `policy1`, `policy2`, `policy3`, `policy4`, `cga`, or `hda` |
| `IDYN_EXPERTS` | `6` | Number of expert deployments |
| `IDYN_HOT_EXPERTS` | `0,1` | Experts treated as hot for placement affinity |
| `MOE_IMAGE` | `moe-serving:latest` | Image used by generated deployments |
| `IDYN_MANIFEST` | `/tmp/idyn-moe-serving-$namespace.yaml` | Rendered manifest path |
| `IDYN_ROLLOUT_TIMEOUT` | `240s` | Rollout timeout for `kubectl` |

## 3. Live Physical Policy Comparison

The physical runner compares all benchmark policies and writes a complete run
ledger. It uses `python:3.11-slim` by default and mounts `server.py` through a
ConfigMap, so it does not require a custom benchmark image.

```bash
IDYN_LIVE_PHYSICAL=1 \
IDYN_SCALE=scale10 \
IDYN_REPLICA_PROFILE=replica1 \
IDYN_SKEW_MODE=phase_shift \
IDYN_REQUESTS=120 \
IDYN_QPS=10 \
IDYN_EXPERTS=6 \
  benchmarks/moe-serving/scripts/reproduce.sh
```

The runner requires exactly the requested number of ready nodes with the
matching scale label. For `scale10`, it expects 10 ready nodes selected by
`idynamics.dev/scale10=true`.

It compares:

- Kubernetes default
- CGA
- HDA
- Policy 2 critical-path latency
- Policy 3 bandwidth/payload-aware

Only run one live cluster experiment at a time. The physical runner uses
`/tmp/idyn-locks/experiment.lock` and removes temporary
`idynamics.io/placement-group` node labels during cleanup.

## Troubleshooting

- Pending pods usually mean the image cannot be pulled or the node selector
  label does not match any ready worker.
- `kubectl top` failures are archived as `.err` files and do not stop metric
  collection.
- Port-forward failures usually mean `svc/frontend` is not ready or another
  process is using `IDYN_LOCAL_PORT`.
- If a physical run aborts, inspect `commands.log`, `logs/`, and the namespace
  events in `raw/*_events.txt` or `raw/*_pods.json`.
