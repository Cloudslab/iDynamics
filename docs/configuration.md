# Configuration

[Documentation index](index.md) | [Architecture](architecture.md) | [Policy development](policy-development.md)

iDynamics configuration is split across Python package extras, benchmark adapter
YAML, shell-script environment variables, trace-provider parameters, policy
input JSON, and run-ledger metadata.

## Python Extras

Package extras are declared in `setup.cfg`:

| Extra | Purpose |
| --- | --- |
| `analysis` | Plotting, graph, dataframe, and Prometheus client dependencies. |
| `cluster` | Python Kubernetes and SSH-related client libraries for live helpers. |
| `dev` | Test and wheel-building dependencies. |

Examples:

```bash
python3 -m pip install -e ".[dev,analysis]"
python3 -m pip install -e ".[cluster]"
```

## Benchmark Script Variables

All benchmark scripts source `benchmarks/_lib/benchmark.sh` and support
`--help`. Common options can also be supplied through environment variables.

| Variable | Meaning | Default or constraint |
| --- | --- | --- |
| `IDYN_NAMESPACE` | Kubernetes namespace override. | Must match `idyn-*`. |
| `IDYN_EXTERNAL_ROOT` | Parent directory for third-party source checkouts. | `external/benchmarks`. |
| `IDYN_CLEANUP` | Delete namespace after `reproduce.sh` when set to `1`. | Off. |
| `IDYN_SKIP_FETCH` | Require an existing source checkout instead of fetching. | Off. |
| `IDYN_DURATION_SECONDS` | Load duration for helper-generated HTTP load. | `45`. |
| `IDYN_CONCURRENCY` | HTTP load helper concurrency. | `4`. |
| `IDYN_LOCAL_PORT` | Local port for `kubectl port-forward`. | `18080`. |
| `IDYN_SCALE` | Optional node-selector label suffix such as `scale45`. | Empty. |
| `IDYN_REPLICA_PROFILE` | Adapter replica profile name. | `replica1`. |

Cluster mutation helpers reject unsafe namespaces such as `default`,
`kube-system`, `istio-system`, and names outside the `idyn-*` pattern.

## Adapter Files

Each benchmark has a stable folder contract:

- `metadata.yaml` records source, pinned commit or local path, deployment
  method, namespace, entry service, license, telemetry expectations, and known
  limitations.
- `adapter/service_map.yaml` names services and expected edges for graph and
  policy interpretation.
- `adapter/workload_mix.yaml` defines request classes and load paths.
- `adapter/replica_profiles.yaml` defines deployment scale presets used by
  experiments or scripts.

Keep adapter YAML declarative. Cluster-specific access material, command
histories, and raw environment dumps do not belong in adapter files.

## Policy Input JSON

`scripts/policies/run_policy.py` accepts a JSON document with:

- `nodes`: list of `NodeInfo` fields;
- `pods`: list of `PodInfo` fields;
- `service_graph`: optional `services` and `edges`;
- `network`: optional node names, latency matrix, and bandwidth matrix.

Minimal shape:

```json
{
  "nodes": [
    {"name": "node-a", "cpu_capacity_millicores": 2000, "memory_capacity_mib": 4096}
  ],
  "pods": [
    {"name": "frontend", "namespace": "demo", "service": "frontend", "cpu_request_millicores": 500, "memory_request_mib": 256}
  ]
}
```

Use labels to lock a pod to its existing node during planning:

```json
{"idynamics.io/locked": "true"}
```

## Trace Providers

Trace providers are configured through constructor arguments in Python:

```python
from idynamics.network.traces import BurstCorrelatedProvider

provider = BurstCorrelatedProvider(
    num_nodes=10,
    steps=120,
    interval_s=5.0,
    seed=11,
)
```

Every provider exposes `frames()` and `metadata()`. Archive provider metadata
with run outputs whenever trace-derived results are used in an experiment.

## Run Ledger Metadata

Use `idynamics.ledger.run.init_run_ledger()` to create the standard layout:

```python
from idynamics.ledger.run import init_run_ledger, log_command

ledger = init_run_ledger("example-run", purpose="policy smoke")
log_command(ledger, "python3 scripts/policies/run_policy.py --policy policy4 --demo moe")
```

Required ledger files are listed in [Architecture](architecture.md#run-ledgers).
The ledger is the place to preserve configuration, command provenance, code
state, and claim boundaries for a run.
