"""Fast local prechecks before experiments."""

from __future__ import annotations

from pathlib import Path


def check_experiment_preconditions(root: Path) -> list[str]:
    """Return precheck failures without mutating cluster state."""
    required = [
        root / "pyproject.toml",
        root / "Makefile",
        root / "src" / "idynamics",
    ]
    failures = [f"missing required path: {path}" for path in required if not path.exists()]
    if not (root / "experiments" / "runs").is_dir():
        failures.append("missing experiments/runs ledger root")
    return failures
