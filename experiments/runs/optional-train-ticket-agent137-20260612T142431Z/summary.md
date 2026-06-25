# Optional TrainTicket Compatibility Attempt

Run ID: `optional-train-ticket-agent137-20260612T142431Z`

This run attempted exactly one optional external benchmark: TrainTicket.

The deployment applied the TrainTicket Kubernetes/Istio manifests into
namespace `idyn-train-ticket-agent137`. The deploy script exited with status
`0`, but its rollout wait was ineffective because `kubectl rollout status
deployment --all` was rejected by this kubectl. A manual readiness wait was run
and timed out with exit status `1`.

The `ts-ui-dashboard` endpoint passed smoke testing and a single 30-second HTTP
dashboard-root probe. The full application was not healthy: several backend
service pods entered restart/backoff states, so this is compatibility evidence
only.

Cleanup completed with exit status `0`, and namespace deletion was verified.

No performance claim is supported by this run.
