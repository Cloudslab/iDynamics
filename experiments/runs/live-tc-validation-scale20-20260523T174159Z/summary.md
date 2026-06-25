# live-tc-validation-scale20-20260523T174159Z

Status: completed

## Purpose
Validate destination-specific live tc delay application on worker-only `scale20`.

## Result
- Mean RTT before tc: 1.34 ms.
- Mean RTT during tc: 41.40 ms.
- Expected RTT during tc: 41.34 ms.
- Target-vs-measured error: 0.06 ms.
- Mean RTT after reset: 1.11 ms.
- Reset residual: -0.23 ms.

## Safety
Qdisc snapshots were captured before application, after application, before reset, and after reset. The injector only installed filters for selected worker destination node IPs; control-plane, Kubernetes service IPs, DNS ClusterIP, and SSH/control traffic to the master were not filter targets.
