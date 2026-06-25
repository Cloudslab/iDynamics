from idynamics.workloads.adapters import ADAPTERS, get_adapter, iter_adapters


def test_external_adapter_registry_contains_requested_benchmarks() -> None:
    assert {"online_boutique", "deathstar_hotel", "deathstar_media", "social_network", "train_ticket", "sock_shop"} <= set(ADAPTERS)
    assert get_adapter("online_boutique").priority == "primary"
    assert get_adapter("sock_shop").priority == "archived-compatibility"
    assert get_adapter("social_network").priority == "requested-real-benchmark"


def test_online_boutique_adapter_exposes_grpc_surface_and_workload_controls() -> None:
    adapter = get_adapter("online_boutique")

    grpc_endpoints = [endpoint for endpoint in adapter.endpoints if endpoint.protocol == "gRPC"]
    command = adapter.workload_command_templates()[0]

    assert adapter.service_count == 12
    assert len(grpc_endpoints) >= 8
    assert "USERS={users}" in command
    assert "RATE={rate}" in command
    assert "frontend:80" in command


def test_adapter_apply_and_delete_commands_are_reversible() -> None:
    adapter = get_adapter("deathstar_hotel")

    apply_commands = adapter.apply_commands(namespace="idyn-general")
    delete_commands = adapter.delete_commands(namespace="idyn-general")

    assert apply_commands == ("kubectl apply -n idyn-general -f /home/ubuntu/idyn-external/deathstarbench/hotelReservation/kubernetes",)
    assert delete_commands == ("kubectl delete -n idyn-general -f /home/ubuntu/idyn-external/deathstarbench/hotelReservation/kubernetes --ignore-not-found",)


def test_iter_adapters_filters_priority() -> None:
    primary = iter_adapters(priorities=("primary",))

    assert [adapter.key for adapter in primary] == ["online_boutique"]
