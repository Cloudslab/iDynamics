# TrainTicket Compatibility Adapter

TrainTicket is a complex compatibility adapter. It has a large service and
database footprint, so use it only after primary Online Boutique, Social
Network, and MoE runs are stable.

## Quick Start

```bash
IDYN_SCALE=scale45 IDYN_CLEANUP=1 benchmarks/train-ticket/scripts/reproduce.sh
```

Expected local checkout:
`/home/ubuntu/idyn-external/train-ticket`.

The runner writes a ledger under `experiments/runs/gda-real-train-ticket-*`.
If upstream services do not become Available, the ledger is still useful as a
deployment-blocked artifact containing manifests, Kubernetes state, events, and
rollout logs.

## Claim Boundary

Use a Train Ticket row in the paper only when the ledger status is `measured`.
Rows with `deploy_blocked`, `load_blocked`, or `telemetry_blocked` document
best-effort reproducibility but do not support a successful overhead claim.
