"""Network trace provider compatibility layer."""

from iDynamicsPackagesModules.NetworkingDynamicsManager.network_trace_provider import (
    BurstCorrelatedProvider,
    CsvMatrixReplayProvider,
    NetworkTraceProvider,
    NetworkTraceFrame,
    SyntheticDistanceRandomProvider,
    coefficient_of_variation,
    compute_network_metrics,
    lag1_autocorrelation,
    pearson_correlation,
    percentile,
    spatial_correlation,
    temporal_autocorrelation,
    write_frames_csv,
    write_metrics_json,
)

__all__ = [
    "BurstCorrelatedProvider",
    "CsvMatrixReplayProvider",
    "NetworkTraceProvider",
    "NetworkTraceFrame",
    "SyntheticDistanceRandomProvider",
    "coefficient_of_variation",
    "compute_network_metrics",
    "lag1_autocorrelation",
    "pearson_correlation",
    "percentile",
    "spatial_correlation",
    "temporal_autocorrelation",
    "write_frames_csv",
    "write_metrics_json",
]
