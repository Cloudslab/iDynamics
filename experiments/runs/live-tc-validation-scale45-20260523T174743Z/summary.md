# live-tc-validation-scale45-20260523T174743Z

Status: completed

## Purpose
Validate destination-specific live tc delay application on worker-only `scale45`.

## Result
- Mean RTT before tc: 1.00 ms.
- Mean RTT during tc: 41.29 ms.
- Expected RTT during tc: 41.00 ms.
- Target-vs-measured error: 0.29 ms.
- Mean RTT after reset: 1.45 ms.
- Reset residual: 0.45 ms.

## Safety
Qdisc snapshots were captured before application, after application, before reset, and after reset. The injector only installed filters for selected worker destination node IPs; control-plane, Kubernetes service IPs, DNS ClusterIP, and SSH/control traffic to the master were not filter targets.
