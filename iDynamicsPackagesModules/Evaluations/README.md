# Main Evaluation Steps

## (0) Chang with different cluster node settings (5 nodes, 10 nodes and 15 nodes)

## (1) Install microservice applications
Use helm to install socialnetwork app in different namespaces.
Each app is managed by a scheduling policy in a unique namespace
For example, namespace 
> **Alternatively install**: using --set instead of --set-string to allow Helm to correctly parse the nested structure:\
$ helm install RELEASE_NAME HELM_CHART_REPO_PATH \
--namespace YOUR_NAMESPACE \
--set global.resources.requests.memory=64Mi \
--set global.resources.requests.cpu=150m \
--set global.resources.limits.memory=256Mi \
--set global.resources.limits.cpu=300m \
--set compose-post-service.container.resources.requests.memory=64Mi \
--set compose-post-service.container.resources.requests.cpu=300m \
--set compose-post-service.container.resources.limits.memory=256Mi \
--set compose-post-service.container.resources.limits.cpu=500m

For example, navigate to the path with 'socialnetwork' app helm chart.
'''
ubuntu@k8s-master:~/DeathStarBench/socialNetwork/helm-chart$ helm install social-net1 socialnetwork/ \
--namespace social-network \
--set global.resources.requests.memory=64Mi \
--set global.resources.requests.cpu=150m \
--set global.resources.limits.memory=256Mi \
--set global.resources.limits.cpu=300m \
--set compose-post-service.container.resources.requests.memory=64Mi \
--set compose-post-service.container.resources.requests.cpu=300m \
--set compose-post-service.container.resources.limits.memory=256Mi \
--set compose-post-service.container.resources.limits.cpu=500m
NAME: social-net1
LAST DEPLOYED: Fri Jul  4 13:43:54 2025
NAMESPACE: social-network
STATUS: deployed
REVISION: 1
TEST SUITE: None

'''
> **Alternatively upgrade**: Upgrade existing RELEASE via helm upgrade:\
$ helm upgrade social-net3 ./socialnetwork \
--namespace social-network3 \
--set global.resources.requests.memory=64Mi \
--set global.resources.requests.cpu=100m \
--set global.resources.limits.memory=128Mi \
--set global.resources.limits.cpu=200m \

helm upgrade social-net3 ./socialnetwork \
--namespace social-network3 \
--set global.resources.requests.memory=128Mi \
--set global.resources.requests.cpu=200m \
--set global.resources.limits.memory=256Mi \
--set global.resources.limits.cpu=400m \
--set jaeger.container.resources.requests.memory= 1024Mi \
--set jaeger.container.resources.requests.cpu=500m \
--set jaeger.container.resources.limits.memory= 2048 Mi \
--set jaeger.container.resources.limits.cpu=1000m