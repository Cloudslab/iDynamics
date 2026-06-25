# physical-moe-size5-20260521T112505Z

Status: failed

## Purpose
Initial physical size5 MoE Kubernetes run attempt.

## Result
The run failed before workload pods were created because the cluster did not accept the namespace and namespaced resources in one manifest apply operation. The runner was patched to create the namespace explicitly before applying namespaced resources.

## Limitations
No paper claims are supported by this failed run. It was superseded by `physical-moe-size5-20260521T112541Z`.
