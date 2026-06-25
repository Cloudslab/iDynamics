"""Registry for external benchmark adapters selected for iDynamics."""

from __future__ import annotations

from collections.abc import Iterable

from idynamics.workloads.adapters.base import BenchmarkAdapter, EndpointSpec, WorkloadGeneratorSpec


ONLINE_BOUTIQUE = BenchmarkAdapter(
    key="online_boutique",
    display_name="Online Boutique / Google Microservices Demo",
    priority="primary",
    source_url="https://github.com/GoogleCloudPlatform/microservices-demo.git",
    source_commit="5096a85b2f3bf41bef53363cfe5478d5b86ac701",
    license="Apache-2.0",
    local_path="/home/ubuntu/idyn-external/online-boutique",
    manifest_paths=(
        "/home/ubuntu/idyn-external/online-boutique/kubernetes-manifests",
        "/home/ubuntu/idyn-external/online-boutique/istio-manifests",
    ),
    service_count=12,
    application_services=(
        "adservice",
        "cartservice",
        "checkoutservice",
        "currencyservice",
        "emailservice",
        "frontend",
        "loadgenerator",
        "paymentservice",
        "productcatalogservice",
        "recommendationservice",
        "shippingservice",
    ),
    dependency_services=("redis-cart",),
    required_images=(
        "adservice",
        "cartservice",
        "checkoutservice",
        "currencyservice",
        "emailservice",
        "frontend",
        "loadgenerator",
        "paymentservice",
        "productcatalogservice",
        "recommendationservice",
        "redis:alpine",
        "shippingservice",
    ),
    endpoints=(
        EndpointSpec("frontend-http", "frontend", 80, "HTTP", "/"),
        EndpointSpec("frontend-external-http", "frontend-external", 80, "HTTP", "/"),
        EndpointSpec("adservice-grpc", "adservice", 9555, "gRPC"),
        EndpointSpec("cartservice-grpc", "cartservice", 7070, "gRPC"),
        EndpointSpec("checkoutservice-grpc", "checkoutservice", 5050, "gRPC"),
        EndpointSpec("currencyservice-grpc", "currencyservice", 7000, "gRPC"),
        EndpointSpec("emailservice-grpc", "emailservice", 5000, "gRPC"),
        EndpointSpec("paymentservice-grpc", "paymentservice", 50051, "gRPC"),
        EndpointSpec("productcatalogservice-grpc", "productcatalogservice", 3550, "gRPC"),
        EndpointSpec("recommendationservice-grpc", "recommendationservice", 8080, "gRPC"),
        EndpointSpec("shippingservice-grpc", "shippingservice", 50051, "gRPC"),
    ),
    workload_generators=(
        WorkloadGeneratorSpec(
            name="in-cluster-locust",
            tool="Locust FastHttpUser",
            source_path="/home/ubuntu/idyn-external/online-boutique/src/loadgenerator/locustfile.py",
            command_template="kubectl -n {namespace} set env deployment/loadgenerator USERS={users} RATE={rate} FRONTEND_ADDR=frontend:80",
            options=("USERS", "RATE", "FRONTEND_ADDR"),
            notes="Default manifest uses USERS=10 and RATE=1 against frontend:80.",
        ),
    ),
    resource_requirements=(
        "Typical application container request: 100m-300m CPU and 64Mi-256Mi memory.",
        "recommendationservice requests 100m CPU/220Mi memory and limits 200m CPU/450Mi memory.",
        "loadgenerator requests 300m CPU/256Mi memory and limits 500m CPU/512Mi memory.",
    ),
    telemetry_labels=("app=<service>", "sidecar.istio.io/rewriteAppHTTPProbers=true"),
    known_risks=(
        "Checked-out Kubernetes manifests use local image names; experiments should use the release manifest, Skaffold, Helm values, or a registry rewrite before applying to a fresh cluster.",
        "The load generator exercises the HTTP frontend; service-to-service traffic is mostly gRPC and should be measured from mesh telemetry.",
        "Optional Google Cloud Operations and managed backing-service overlays should remain disabled for the default local-cluster experiment.",
    ),
    selection_notes="Best primary candidate: Kubernetes-native, actively maintained, compact enough for 5-node smoke runs, and rich in gRPC edges for Istio telemetry.",
)


DEATHSTAR_HOTEL = BenchmarkAdapter(
    key="deathstar_hotel",
    display_name="DeathStarBench Hotel Reservation",
    priority="secondary",
    source_url="https://github.com/delimitrou/DeathStarBench.git",
    source_commit="6ecb09706140f8730b5385c08f1386c654c3c526",
    license="Apache-2.0",
    local_path="/home/ubuntu/idyn-external/deathstarbench",
    manifest_paths=("/home/ubuntu/idyn-external/deathstarbench/hotelReservation/kubernetes",),
    service_count=19,
    application_services=("frontend", "geo", "profile", "rate", "recommendation", "reservation", "search", "user"),
    dependency_services=(
        "consul",
        "jaeger",
        "memcached-profile",
        "memcached-rate",
        "memcached-reserve",
        "mongodb-geo",
        "mongodb-profile",
        "mongodb-rate",
        "mongodb-recommendation",
        "mongodb-reservation",
        "mongodb-user",
    ),
    required_images=("deathstarbench/hotel-reservation:latest", "hashicorp/consul:latest", "jaegertracing/all-in-one:latest", "memcached", "mongo:4.4.6"),
    endpoints=(EndpointSpec("frontend-http", "frontend", 5000, "HTTP", "/"), EndpointSpec("jaeger-ui", "jaeger", 16686, "HTTP", "/")),
    workload_generators=(
        WorkloadGeneratorSpec(
            name="wrk2-mixed",
            tool="wrk2",
            source_path="/home/ubuntu/idyn-external/deathstarbench/hotelReservation/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua",
            command_template="{wrk2} -D exp -t {threads} -c {connections} -d {duration} -L -s hotelReservation/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua http://{frontend_host}:5000 -R {rate}",
            options=("threads", "connections", "duration", "rate", "frontend_host"),
        ),
    ),
    resource_requirements=("Manifest requests 100m CPU and limits 1000m CPU on each deployment; memory requests are mostly absent.", "Requires persistent volume objects for MongoDB state."),
    telemetry_labels=("io.kompose.service=<service>", "sidecar.istio.io/statsInclusionRegexps=http.*"),
    known_risks=(
        "Kubernetes manifests originate from Kompose and include host-path style persistent-volume assumptions.",
        "Consul and Jaeger are part of the deployment and can skew mesh overhead measurements unless isolated.",
        "The service is HTTP/RPC rather than gRPC-heavy; use as secondary generality evidence.",
    ),
    selection_notes="Good secondary candidate when stateful dependencies are acceptable and DeathStarBench comparability matters.",
)


DEATHSTAR_MEDIA = BenchmarkAdapter(
    key="deathstar_media",
    display_name="DeathStarBench Media Microservices",
    priority="secondary",
    source_url="https://github.com/delimitrou/DeathStarBench.git",
    source_commit="6ecb09706140f8730b5385c08f1386c654c3c526",
    license="Apache-2.0",
    local_path="/home/ubuntu/idyn-external/deathstarbench",
    manifest_paths=("/home/ubuntu/idyn-external/deathstarbench/mediaMicroservices/openshift",),
    service_count=33,
    application_services=(
        "cast-info-service",
        "compose-review-service",
        "movie-id-service",
        "movie-info-service",
        "movie-review-service",
        "nginx-web-server",
        "plot-service",
        "rating-service",
        "review-storage-service",
        "text-service",
        "unique-id-service",
        "user-review-service",
        "user-service",
    ),
    dependency_services=(
        "jaeger",
        "memcached services",
        "mongodb services",
        "redis services",
        "mms-client",
    ),
    required_images=("deathstarbench/wrk2-client", "jaegertracing/all-in-one:latest", "memcached", "mongo:4.4.6", "redis", "yg397/media-microservices", "yg397/openresty-thrift:xenial"),
    endpoints=(EndpointSpec("nginx-http", "nginx-web-server", 8080, "HTTP", "/"), EndpointSpec("jaeger-ui", "jaeger-out", 16686, "HTTP", "/")),
    workload_generators=(
        WorkloadGeneratorSpec(
            name="wrk2-compose-review",
            tool="wrk2",
            source_path="/home/ubuntu/idyn-external/deathstarbench/mediaMicroservices/wrk2/scripts/media-microservices/compose-review.lua",
            command_template="{wrk2} -D exp -t {threads} -c {connections} -d {duration} -L -s mediaMicroservices/wrk2/scripts/media-microservices/compose-review.lua http://{nginx_host}:8080 -R {rate}",
            options=("threads", "connections", "duration", "rate", "nginx_host"),
        ),
    ),
    resource_requirements=("No explicit CPU/memory requests in the inspected OpenShift manifests.", "Many database/cache deployments; reserve several nodes for non-application dependencies in scale tests."),
    telemetry_labels=("app=<service>", "death-star-project=media-microsvc", "sidecar.istio.io/inject=true"),
    known_risks=(
        "Manifests are under openshift/ and include Route objects and OpenShift helper scripts.",
        "Larger stateful footprint makes it a poor first target for fast 5/10 worker smoke runs.",
        "Requires data bootstrap scripts for meaningful workload behavior.",
    ),
    selection_notes="Secondary only: strong microservice graph, but more operational risk than Online Boutique.",
)


DEATHSTAR_SOCIAL_NETWORK = BenchmarkAdapter(
    key="social_network",
    display_name="DeathStarBench Social Network",
    priority="requested-real-benchmark",
    source_url="https://github.com/delimitrou/DeathStarBench.git",
    source_commit="6ecb09706140f8730b5385c08f1386c654c3c526",
    license="Apache-2.0",
    local_path="/home/ubuntu/idyn-external/deathstarbench/socialNetwork",
    manifest_paths=("/home/ubuntu/idyn-external/deathstarbench/socialNetwork/helm-chart/socialnetwork",),
    service_count=28,
    application_services=(
        "nginx-thrift",
        "compose-post-service",
        "home-timeline-service",
        "user-timeline-service",
        "user-service",
        "text-service",
        "unique-id-service",
        "media-service",
        "post-storage-service",
        "social-graph-service",
        "url-shorten-service",
        "user-mention-service",
    ),
    dependency_services=(
        "jaeger",
        "media-frontend",
        "memcached services",
        "mongodb services",
        "redis services",
    ),
    required_images=(
        "deathstarbench/social-network-microservices:latest",
        "yg397/openresty-thrift:xenial",
        "yg397/media-frontend:xenial",
        "mongo:4.4.6",
        "memcached:1.6.7",
        "redis:6.2.4",
    ),
    endpoints=(
        EndpointSpec("nginx-thrift", "nginx-thrift", 8080, "HTTP/OpenResty-Thrift", "/wrk2-api/home-timeline/read"),
        EndpointSpec("media-frontend", "media-frontend", 8081, "HTTP/OpenResty-Thrift", "/"),
    ),
    workload_generators=(
        WorkloadGeneratorSpec(
            name="bounded-social-mix",
            tool="Python HTTP client or wrk2",
            source_path="/home/ubuntu/idyn-external/deathstarbench/socialNetwork/wrk2/scripts/social-network/mixed-workload.lua",
            command_template="python3 scripts/experiments/real_benchmark_gda_overhead.py --benchmark social-network --scale {scale}",
            options=("scale", "duration", "concurrency"),
            notes="The ledger runner emits compose-post, read-home-timeline, and read-user-timeline requests.",
        ),
    ),
    resource_requirements=("Helm chart default global request is 100m CPU and 128Mi memory per container.",),
    telemetry_labels=("source_workload", "destination_workload", "app.kubernetes.io/name"),
    known_risks=(
        "The Helm chart init containers clone DeathStarBench assets at pod startup.",
        "Stateful MongoDB/Redis/memcached dependencies can dominate readiness time.",
        "Use blocked ledgers as operational evidence only.",
    ),
    selection_notes="Requested real DeathStarBench benchmark for live GDA overhead evaluation.",
)


TRAIN_TICKET = BenchmarkAdapter(
    key="train_ticket",
    display_name="TrainTicket",
    priority="complex-smoke",
    source_url="https://github.com/FudanSELab/train-ticket.git",
    source_commit="313886e99befb94be6cd45f085c98e0019f59829",
    license="Apache-2.0",
    local_path="/home/ubuntu/idyn-external/train-ticket",
    manifest_paths=("/home/ubuntu/idyn-external/train-ticket/deployment/kubernetes-manifests/k8s-with-istio",),
    service_count=64,
    application_services=(
        "ts-admin-basic-info-service",
        "ts-admin-order-service",
        "ts-admin-route-service",
        "ts-admin-travel-service",
        "ts-admin-user-service",
        "ts-assurance-service",
        "ts-auth-service",
        "ts-basic-service",
        "ts-cancel-service",
        "ts-config-service",
        "ts-contacts-service",
        "ts-order-service",
        "ts-payment-service",
        "ts-preserve-service",
        "ts-route-service",
        "ts-ticketinfo-service",
        "ts-travel-service",
        "ts-ui-dashboard",
        "ts-user-service",
    ),
    dependency_services=("22 MongoDB services", "ts-voucher-mysql"),
    required_images=("codewisdom/ts-*-service:0.0.4", "codewisdom/ts-avatar-service:0.1.0", "mongo", "mysql:5.6.35"),
    endpoints=(EndpointSpec("ui-dashboard", "ts-ui-dashboard", 8080, "HTTP", "/"), EndpointSpec("istio-gateway", "trainticket-gateway", 80, "HTTP", "/")),
    workload_generators=(
        WorkloadGeneratorSpec(
            name="gateway-http-smoke",
            tool="curl/HTTP client",
            source_path="/home/ubuntu/idyn-external/train-ticket/ts-gateway-service/src/main/resources/application.yml",
            command_template="curl -fsS http://{gateway_host}:{gateway_port}/api/v1/users/login",
            options=("gateway_host", "gateway_port"),
            notes="No maintained in-repo load generator was found in the inspected checkout; use smoke and custom trace replay only.",
        ),
    ),
    resource_requirements=("Most database manifests request 50m CPU and 100Mi memory.", "Large deployment count means this should start at 20+ workers, not as the primary smoke benchmark."),
    telemetry_labels=("app=<service>",),
    known_risks=(
        "Older repository and image set; many services and databases increase image-pull and readiness failure probability.",
        "No clear maintained workload generator in the inspected checkout.",
        "Large blast radius makes it unsuitable for routine iterative experiments.",
    ),
    selection_notes="Use as a complex compatibility smoke only after Online Boutique is stable.",
)


SOCK_SHOP = BenchmarkAdapter(
    key="sock_shop",
    display_name="Sock Shop",
    priority="archived-compatibility",
    source_url="https://github.com/microservices-demo/microservices-demo.git",
    source_commit="9dff06fae4981921caec6a62393a6ebfce4b3e3f",
    license="Apache-2.0",
    local_path="/home/ubuntu/idyn-external/sock-shop",
    manifest_paths=(
        "/home/ubuntu/idyn-external/sock-shop/deploy/kubernetes/manifests",
        "/home/ubuntu/idyn-external/sock-shop/deploy/kubernetes/manifests-loadtest",
    ),
    service_count=14,
    application_services=("carts", "catalogue", "front-end", "orders", "payment", "queue-master", "shipping", "user"),
    dependency_services=("carts-db", "catalogue-db", "orders-db", "rabbitmq", "session-db", "user-db"),
    required_images=(
        "kbudde/rabbitmq-exporter",
        "mongo",
        "rabbitmq:3.6.8-management",
        "redis:alpine",
        "weaveworksdemos/carts:0.4.8",
        "weaveworksdemos/catalogue-db:0.3.0",
        "weaveworksdemos/catalogue:0.3.5",
        "weaveworksdemos/front-end:0.3.12",
        "weaveworksdemos/orders:0.4.7",
        "weaveworksdemos/payment:0.4.3",
        "weaveworksdemos/queue-master:0.3.1",
        "weaveworksdemos/shipping:0.4.8",
        "weaveworksdemos/user-db:0.3.0",
        "weaveworksdemos/user:0.4.7",
    ),
    endpoints=(EndpointSpec("frontend-http", "front-end", 80, "HTTP", "/"),),
    workload_generators=(
        WorkloadGeneratorSpec(
            name="load-test-locust",
            tool="Locust",
            source_path="/home/ubuntu/idyn-external/sock-shop/deploy/kubernetes/manifests-loadtest/loadtest-dep.yaml",
            command_template="locust --host http://front-end.sock-shop.svc.cluster.local -f /config/locustfile.py --clients {clients} --hatch-rate {hatch_rate} --num-request {requests} --no-web",
            options=("clients", "hatch_rate", "requests"),
            notes="Manifest default loops with clients=5, hatch-rate=5, num-request=100.",
        ),
    ),
    resource_requirements=("Main app services request about 99m-100m CPU and 100Mi-300Mi memory; some services limit at 200m-500m CPU.", "Load-test pod requests 100m CPU/300Mi memory and limits 300m CPU/1000Mi memory."),
    telemetry_labels=("name=<service>", "prometheus.io/scrape=true on service objects"),
    known_risks=(
        "Repository HEAD contains an explicit deprecation notice.",
        "REST-only architecture is less aligned with the paper's gRPC/Istio focus.",
        "Older images and Kubernetes assumptions may need compatibility patches.",
    ),
    selection_notes="Compatibility baseline only; do not lead reported results with this benchmark.",
)


ADAPTERS: dict[str, BenchmarkAdapter] = {
    adapter.key: adapter
    for adapter in (ONLINE_BOUTIQUE, DEATHSTAR_HOTEL, DEATHSTAR_MEDIA, DEATHSTAR_SOCIAL_NETWORK, TRAIN_TICKET, SOCK_SHOP)
}


def get_adapter(key: str) -> BenchmarkAdapter:
    try:
        return ADAPTERS[key]
    except KeyError as exc:
        available = ", ".join(sorted(ADAPTERS))
        raise KeyError(f"unknown external benchmark adapter {key!r}; available: {available}") from exc


def iter_adapters(priorities: Iterable[str] | None = None) -> tuple[BenchmarkAdapter, ...]:
    adapters = tuple(ADAPTERS.values())
    if priorities is None:
        return adapters
    allowed = set(priorities)
    return tuple(adapter for adapter in adapters if adapter.priority in allowed)
