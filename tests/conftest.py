from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("IDYNAMICS_RUN_LIVE_CLUSTER") == "1":
        return

    skip_live = pytest.mark.skip(reason="set IDYNAMICS_RUN_LIVE_CLUSTER=1 to run live Kubernetes tests")
    for item in items:
        if "live_cluster" in item.keywords:
            item.add_marker(skip_live)
