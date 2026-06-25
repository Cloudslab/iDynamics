import csv

from idynamics.network.traces import (
    BurstCorrelatedProvider,
    CsvMatrixReplayProvider,
    NetworkTraceProvider,
    SyntheticDistanceRandomProvider,
    compute_network_metrics,
    write_frames_csv,
)


def test_providers_implement_trace_interface() -> None:
    assert issubclass(SyntheticDistanceRandomProvider, NetworkTraceProvider)
    assert issubclass(BurstCorrelatedProvider, NetworkTraceProvider)
    assert issubclass(CsvMatrixReplayProvider, NetworkTraceProvider)


def test_burst_correlated_metrics_include_reviewer_statistics() -> None:
    frames = list(BurstCorrelatedProvider(num_nodes=4, steps=18, interval_s=2.0, seed=9).frames())
    metrics = compute_network_metrics(frames)

    for metric in ("latency_ms", "bandwidth_mbps"):
        values = metrics[metric]
        assert values["p50"] > 0
        assert values["p95"] >= values["p50"]
        assert values["p99"] >= values["p95"]
        assert values["coefficient_of_variation"] >= 0
        assert "peak_to_median" in values
        assert "lag1_autocorrelation" in values
        assert "spatial_correlation" in values
        assert "burst_duration_s" in values
        assert "recovery_time_s" in values


def test_csv_matrix_replay_round_trip(tmp_path) -> None:
    frames = list(SyntheticDistanceRandomProvider(num_nodes=3, steps=2, seed=4).frames())
    path = tmp_path / "trace.csv"
    write_frames_csv(frames, path)

    replayed = list(CsvMatrixReplayProvider(path).frames())

    assert len(replayed) == len(frames)
    assert replayed[0].latency_ms == frames[0].latency_ms
    assert replayed[1].bandwidth_mbps == frames[1].bandwidth_mbps


def test_csv_matrix_replay_metric_long_format(tmp_path) -> None:
    path = tmp_path / "long.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_s", "metric", "src", "dst", "value"])
        writer.writeheader()
        for metric, value in (("latency_ms", 12.5), ("bandwidth_mbps", 250.0)):
            writer.writerow({"time_s": 0, "metric": metric, "src": 0, "dst": 1, "value": value})
            writer.writerow({"time_s": 0, "metric": metric, "src": 1, "dst": 0, "value": value})

    frame = next(iter(CsvMatrixReplayProvider(path, num_nodes=2).frames()))

    assert frame.latency_ms[0][1] == 12.5
    assert frame.bandwidth_mbps[1][0] == 250.0
