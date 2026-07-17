# Table VI: External latency calibration against RIPE Atlas traces

This folder contains the curated data and deterministic expected output for `tab:ripe_latency_calibration`.

Run `bash run.sh --output-dir generated` from this folder to regenerate the data-only artifact. No public full-cluster rerun script is shipped for this item.

Evidence boundary: Latency-scale calibration against one public RTT sample window only; the fitted generator is not a packet/path replay and does not provide bandwidth calibration.
