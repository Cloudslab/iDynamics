# observability-istio-prometheus-20260521T072000Z

Status: failed

## Purpose
Install Istio service mesh telemetry and Prometheus metric storage for iDynamics TSC revision experiments.

## Result
- Istio 1.30.0 control-plane resources were partially installed.
- The install timed out waiting for `istio-ingressgateway` readiness.
- Installer reported Calico `bpfConnectTimeLoadBalancing=TCP` incompatibility.
- `FelixConfiguration/default` was patched to `bpfConnectTimeLoadBalancing=Disabled`.
- Direct IPPool patch was reverted by the Tigera operator, so `Installation/default` was patched from `VXLANCrossSubnet` to `VXLAN`.
- `calico-node` was rolled after the network configuration changes.
- Cross-node pod routes moved to `vxlan.calico` after the operator-level patch.

## Limitations
- This failed setup run supports only troubleshooting claims.
- A separate retry ledger is required before using mesh telemetry for experiments.
