"""Reusable iDynamics research artifact package.

The package provides typed interfaces and pure utilities used by experiment
scripts. Legacy modules under ``iDynamicsPackagesModules`` remain available,
but new workflows should import through ``idynamics``.
"""

from idynamics._version import __version__
from idynamics.types import (
    ExperimentLedger,
    NetworkMatrix,
    NodeInfo,
    PodInfo,
    SchedulingDecision,
    ServiceGraph,
    TrafficEdge,
)

__all__ = [
    "__version__",
    "ExperimentLedger",
    "NetworkMatrix",
    "NodeInfo",
    "PodInfo",
    "SchedulingDecision",
    "ServiceGraph",
    "TrafficEdge",
]
