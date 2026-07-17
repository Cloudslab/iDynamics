# Table II: Istio sidecar overhead in a controlled Fortio benchmark

This folder contains the curated data and deterministic expected output for `tab:istio_mesh_overhead`.

Run `bash run.sh --output-dir generated` from this folder to regenerate the data-only artifact. No public full-cluster rerun script is shipped for this item.

Evidence boundary: Controlled two-service Fortio no-sidecar versus sidecar path at 5, 20, and 45 worker placement-pool scales; not a universal mesh-overhead estimate for all applications, payloads, or mesh policies.
