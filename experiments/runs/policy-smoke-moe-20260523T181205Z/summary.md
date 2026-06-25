# policy-smoke-moe-20260523T181205Z

Status: completed

## Purpose
Smoke-test executable iDynamics Policy 1-4 planners on a MoE-style service graph with measured-style latency and bandwidth matrices.

## Result
- Policy 1, Policy 2, Policy 3, and Policy 4 each emitted auditable placement decisions.
- Policy 2 distinct from Policy 1: True.
- Policy 3 distinct from Policy 1 and Policy 2: True.
- Kubernetes manifests with policy-specific node-affinity groups were rendered under `raw/`.

## Evidence Boundary
This is a control-plane smoke experiment using a deterministic toy MoE graph and modeled node matrices. It demonstrates that Policies 2 and 3 are executable and behaviorally distinct; it is not a live application latency comparison.
