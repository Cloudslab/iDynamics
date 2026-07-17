# Policy Development

[Documentation index](index.md) | [Configuration](configuration.md) | [Benchmark guide](benchmark-guide.md)

Scheduling policies consume node state, pod state, optional application graph
dynamics, and optional network dynamics. They return auditable placement or
migration decisions.

## Built-In Policies

The built-in planners live in `idynamics.policies.planner`.

| Short name | Class | Inputs emphasized | Intended interpretation |
| --- | --- | --- | --- |
| `policy1` | `Policy1TrafficAffinity` | Service graph stress | CGA: reduce high-stress cross-node call-graph edges. |
| `policy2` | `Policy2LatencyCriticalPath` | Request rate and edge latency | Place latency-critical paths on low-delay node paths. |
| `policy3` | `Policy3BandwidthPayloadAware` | Payload bytes and bandwidth | Avoid assigning high-payload flows to low-bandwidth paths. |
| `policy4` | `Policy4HybridDynamics` | Stress, latency, and bandwidth | HDA: combine graph and network dynamics in one placement objective. |

All four planners share the same capacity-aware greedy framework. CGA and HDA
are the manuscript-facing reference policies; `policy2` and `policy3` are
auxiliary examples for extension and compatibility testing. A pod with label
`idynamics.io/locked=true` and an existing `node_name` is treated as fixed
placement context.

## Modern Policy Protocol

New policies should follow `idynamics.policies.interface.SchedulingPolicy`:

```python
from collections.abc import Sequence

from idynamics.types import NetworkMatrix, NodeInfo, PodInfo, SchedulingDecision, ServiceGraph


class MyPolicy:
    name = "my-policy"

    def plan(
        self,
        pods: Sequence[PodInfo],
        nodes: Sequence[NodeInfo],
        service_graph: ServiceGraph | None = None,
        network: NetworkMatrix | None = None,
    ) -> list[SchedulingDecision]:
        ...
```

`SchedulingDecision` includes `pod_name`, `source_node`, `target_node`,
`policy`, `score`, and a short `reason`, which makes policy output suitable for
run ledgers and replay comparison.

## Running Policies

Use the CLI for built-in planners:

```bash
python3 scripts/policies/run_policy.py --policy policy4 --demo moe
python3 scripts/policies/run_policy.py --policy policy1 --input path/to/input.json --output path/to/plan.json
```

For a new policy, either call it directly from Python or add an explicit factory
entry where your experiment expects to instantiate policies. Do not change the
meaning of existing policy names in archived experiments.

## Legacy Compatibility

Older policy code can still use
`iDynamicsPackagesModules.SchedulingPolicyExtender.my_policy_interface`.
That interface defines:

- `initialize_policy(dynamics_config)`;
- `trigger_migration()`;
- `schedule_pod(pod, candidate_nodes)`;
- `schedule_all(pods, candidate_nodes)`;
- `on_update_metrics(nodes, app_namespace)`;
- `run()`.

Legacy migration helpers patch Kubernetes Deployments through a caller-supplied
API client. Keep live patching separate from offline planning tests so placement
logic can be verified without cluster access.

## GDA And NDM Inputs

GDA provides `ServiceGraph` snapshots with directed `TrafficEdge` weights.
Policies can use:

- `request_rate` for request pressure;
- `sent_bytes_per_s` and `received_bytes_per_s` for payload pressure;
- `stress_bytes_per_s` for symmetric communication stress;
- `latency_ms` for observed application-edge delay when available.

NDM and trace providers provide `NetworkMatrix` snapshots with directed
`latency_ms` and `bandwidth_mbps` matrices. A policy should treat missing
network data conservatively and record that fallback in its decision reason.

## Testing Checklist

Policy tests should cover:

- no feasible node errors;
- locked pod handling;
- deterministic tie breaking;
- behavior with no service graph;
- behavior with no network matrix;
- at least one case where the new policy differs from CGA and HDA when that is
  expected;
- CLI or experiment wiring if the policy is exposed through a script.

Run:

```bash
python3 -m pytest tests/test_policies.py
```
