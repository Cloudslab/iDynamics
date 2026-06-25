# cluster-45node-validation-20260523T161031Z

Status: completed

## Purpose

Validate the expanded 45-worker Kubernetes cluster, create reproducible worker-only node-pool labels, verify node access/tooling, and exercise qdisc snapshot/reset tooling.

## Result

- Observed 45 Ready workers plus 1 Ready control-plane node.
- Verified SSH by InternalIP and passwordless sudo on all 45 workers.
- Verified active kubelet and CRI-O on all 45 workers.
- Verified `ip`, `tc`, and `iperf3` on all 45 workers after installing missing `iperf3`.
- Verified Calico, kube-proxy, CoreDNS, Istio, Prometheus, and DaemonSet readiness after expansion.
- Applied and verified deterministic nested labels for `scale5`, `scale10`, `scale20`, `scale30`, and `scale45`.
- Captured qdisc state for all 45 workers and applied worker-only tc reset with a pre-reset qdisc snapshot.
- Confirmed 45 Ready workers, zero SSH/sudo failures, and zero lingering helper pods after qdisc reset.

## Limitations

- SSH by Kubernetes node name does not resolve from the control-plane host; SSH by InternalIP succeeds.
- No benchmark application pods were scheduled during this validation.
- This run supports cluster-readiness and node-pool reproducibility claims, not benchmark performance claims.
