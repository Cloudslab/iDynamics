# Table III: Overhead of Algorithm 1 on real benchmarks and synthetic service scales

This folder contains the curated data and deterministic expected output for `tab:gda_scalability_overhead_revised`.

Run `bash run.sh --output-dir generated` from this folder to regenerate the data-only artifact. No public full-cluster rerun script is shipped for this item.

Evidence boundary: Real rows measure Prometheus aggregate-query latency plus local graph materialization for the named deployments; synthetic rows isolate local graph construction and logical query-count scaling and do not report live Prometheus latency.
