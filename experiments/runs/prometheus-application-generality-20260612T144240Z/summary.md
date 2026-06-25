# prometheus-application-generality-20260612T144240Z

Status: completed

This ledger archives kube-prometheus-stack range queries for live Online Boutique, live MoE-style, Online Boutique long-mix, and MoE long-mix application-generality windows. It also archives replay-backed GDA runtime distributions from the long-mix source ledgers and live GDA observations from the Online Boutique and MoE source ledgers.

Auxiliary Online Boutique Istio Prometheus query/results from `external-online-boutique-scale20-20260611T123228Z` are copied into `raw/online-boutique-live_istio-prometheus_*` because kube-prometheus-stack did not expose Istio request-rate or request-duration series for the queried windows.

Prometheus evidence is restricted to resource-envelope and runtime-observability support. It is not used as a causal overhead claim.
