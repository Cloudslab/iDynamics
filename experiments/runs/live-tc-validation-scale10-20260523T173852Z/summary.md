# live-tc-validation-scale10-20260523T173852Z

Status: completed

## Purpose
Validate destination-specific live tc delay application on worker-only `scale10`.

## Result
- Mean RTT before tc: 1.52 ms.
- Mean RTT during tc: 41.61 ms.
- Expected RTT during tc: 41.52 ms.
- Target-vs-measured error: 0.09 ms.
- Mean RTT after reset: 1.36 ms.
- Reset residual: -0.16 ms.

## Safety
Qdisc snapshots were captured before application, after application, before reset, and after reset. The injector only installed filters for selected worker destination node IPs; control-plane, Kubernetes service IPs, DNS ClusterIP, and SSH/control traffic to the master were not filter targets.
