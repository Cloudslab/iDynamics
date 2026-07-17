# Quickstart

[Documentation index](index.md) | [Installation](installation.md) | [Benchmark guide](benchmark-guide.md)

This page starts with offline checks that work on a laptop or CI runner, then
shows the live-cluster benchmark path.

## 1. Install The Package

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev,analysis]"
```

## 2. Run A Policy Planner Demo

The policy CLI includes a built-in CPU-only MoE-style placement input. It does
not deploy Kubernetes resources.

```bash
python3 scripts/policies/run_policy.py --policy policy4 --demo moe --output /tmp/idynamics-policy4.json
python3 -m json.tool /tmp/idynamics-policy4.json
```

Try the other built-in planners:

```bash
for policy in policy1 policy2 policy3 policy4; do
  python3 scripts/policies/run_policy.py --policy "$policy" --demo moe >/tmp/"$policy".json
done
```

## 3. Run Offline Tests

```bash
make unit
```

This exercises package imports, policy behavior, trace providers, GDA helpers,
benchmark packaging contracts, workload mixers, and run-ledger utilities without
requiring a cluster.

## 4. Smoke The Artifact Package

```bash
make artifact-smoke
```

The smoke target regenerates a representative table and figure from committed
data, then validates the artifact structure and checksums.

## 5. Try A Network Trace Provider

```bash
python3 - <<'PY'
from idynamics.network.traces import BurstCorrelatedProvider, compute_network_metrics

frames = list(BurstCorrelatedProvider(num_nodes=4, steps=12, seed=11).frames())
print(compute_network_metrics(frames)["latency_ms"]["p95"])
PY
```

Trace providers produce matrices for replay, policy evaluation, or later
traffic-control application. Generating a trace is not the same as mutating a
live network.

## 6. Optional Live Benchmark Smoke

A live benchmark run requires a prepared Kubernetes testbed, `kubectl`, and
application image access. The namespace must match `idyn-*`.

```bash
benchmarks/online-boutique/scripts/fetch.sh
benchmarks/online-boutique/scripts/deploy.sh --namespace idyn-online-boutique
benchmarks/online-boutique/scripts/smoke.sh --namespace idyn-online-boutique
benchmarks/online-boutique/scripts/load.sh --namespace idyn-online-boutique --duration 45 --concurrency 8
benchmarks/online-boutique/scripts/collect.sh --namespace idyn-online-boutique --output-dir experiments/runs/online-boutique-manual
benchmarks/online-boutique/scripts/cleanup.sh --namespace idyn-online-boutique
```

Manual smoke and load output is operational evidence. Treat it as performance
evidence only after it is archived with a complete run ledger and processing
path.

## 7. Next Steps

- Read [Configuration](configuration.md) before changing adapters, traces, or
  policy inputs.
- Read [Policy development](policy-development.md) to implement a new scheduler.
- Read [Reproducibility](reproducibility.md) to regenerate paper-facing
  artifacts from committed data.
