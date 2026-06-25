# social-smoke-scale10-20260523T172628Z

Status: failed

## Blocker
This first attempt failed before workload execution because the runner used `kubectl rollout status deployment --all`, which Kubernetes v1.36 rejects. The runner was corrected to use `kubectl wait --for=condition=available deployment --all`.

## Follow-up
Successful replacement evidence is in `social-smoke-scale10-20260523T172647Z`.
