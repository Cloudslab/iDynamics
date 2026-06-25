import pytest

from idynamics.types import NetworkMatrix, NodeInfo, PodInfo
from idynamics.policies.placement import first_fit_decision, score_node_for_pod


def test_network_matrix_requires_square_matrices() -> None:
    NetworkMatrix.from_lists(("n1", "n2"), [[0, 1], [1, 0]], [[0, 100], [100, 0]])

    with pytest.raises(ValueError):
        NetworkMatrix.from_lists(("n1", "n2"), [[0, 1]], [[0, 100], [100, 0]])

    with pytest.raises(ValueError):
        NetworkMatrix.from_lists(("n1", "n2"), [[0, 1], [1, 0]], [[0, 100, 90], [100, 0, 80]])


def test_first_fit_selects_feasible_highest_residual_node() -> None:
    pod = PodInfo("frontend-0", "social-network", 500, 256)
    nodes = [
        NodeInfo("n1", 1000, 1024, cpu_allocated_millicores=700, memory_allocated_mib=128),
        NodeInfo("n2", 2000, 2048, cpu_allocated_millicores=500, memory_allocated_mib=512),
    ]

    assert score_node_for_pod(nodes[0], pod) == float("-inf")
    decision = first_fit_decision(pod, nodes, policy="test-policy")

    assert decision.target_node == "n2"
    assert decision.policy == "test-policy"
