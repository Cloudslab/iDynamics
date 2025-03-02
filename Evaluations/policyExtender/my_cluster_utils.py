# my_cluster_utils.py

import os
from kubernetes import client, config
from typing import List

# Suppose these are your domain classes or they live in a separate file:
# from my_policy_interface import NodeInfo, PodInfo

class NodeInfo:
    """
    Example domain-specific structure for node information.
    Expand or modify as needed for your scheduling logic.
    """
    def __init__(self, node_name: str,
                 cpu_capacity: float,
                 mem_capacity: float,
                 current_cpu_usage: float,
                 current_mem_usage: float,
                 network_latency=None,
                 network_bandwidth=None):
        self.node_name = node_name
        self.cpu_capacity = cpu_capacity
        self.mem_capacity = mem_capacity
        self.current_cpu_usage = current_cpu_usage
        self.current_mem_usage = current_mem_usage
        # Optional dictionaries or placeholders for additional data
        self.network_latency = network_latency if network_latency else {}
        self.network_bandwidth = network_bandwidth if network_bandwidth else {}

class PodInfo:
    """
    Example domain-specific structure for pod information.
    """
    def __init__(self, pod_name: str,
                 cpu_req: float,
                 mem_req: float,
                 sla_latency_requirement: float,
                 deployment_name: str = None):
        self.pod_name = pod_name
        self.cpu_req = cpu_req
        self.mem_req = mem_req
        self.sla_latency_requirement = sla_latency_requirement
        self.deployment_name = deployment_name

def gather_all_nodes() -> List[client.V1Node]:
    """
    Gather all the Node objects from the Kubernetes cluster.
    Returns:
        A list of raw Kubernetes Node objects.
    """
    # Load config only once at your program entrypoint if possible,
    # or do in-cluster config if running inside the cluster:
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    raw_nodes = v1.list_node().items
    return raw_nodes

def gather_all_pods(namespace: str = None) -> List[client.V1Pod]:
    """
    Gather Pod objects from Kubernetes. If namespace is provided,
    returns pods from that namespace; otherwise returns pods across all namespaces.
    """
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    if namespace: # return Pods from a specific namespace
        raw_pods = v1.list_namespaced_pod(namespace).items
    else: # return Pods from all namespaces
        raw_pods = v1.list_pod_for_all_namespaces().items
    return raw_pods

def build_nodeinfo_objects(raw_nodes: List[client.V1Node]) -> List[NodeInfo]:
    """
    Convert raw Node objects to NodeInfo. You can adapt resource usage logic
    to your environment (e.g. using Metrics API, custom usage collectors, etc.)

    Args:
        raw_nodes: List of Kubernetes node objects.

    Returns:
        A list of NodeInfo objects containing relevant capacity/usage data.
    """
    nodeinfo_list = []

    # If you have a metrics server running, you could fetch live usage.
    # For simplicity, let's just read capacities from node.status.capacity
    # and set usage to 0 or some approximate value.
    # If you want to incorporate usage from metrics, see note below.
    for node in raw_nodes:
        node_name = node.metadata.name
        
        # Example: parse CPU capacity in cores (converting from millicores if needed)
        # Node capacity might be 'cpu': '4', or '4000m' => 4 cores
        cpu_capacity_str = node.status.capacity.get('cpu', '0')
        if cpu_capacity_str.endswith('m'):
            cpu_capacity = float(cpu_capacity_str[:-1]) / 1000.0
        else:
            cpu_capacity = float(cpu_capacity_str)

        # Memory capacity might be Ki, Mi, Gi, etc. Let's assume Ki => convert to Mi
        mem_capacity_str = node.status.capacity.get('memory', '0')
        mem_capacity = _convert_memory_to_mebibytes(mem_capacity_str)

        # Usage can be fetched from metrics if desired:
        # current_cpu_usage, current_mem_usage = fetch_live_node_usage(node_name)
        # For now, let's set them to 0 or placeholders:
        current_cpu_usage = 0.0
        current_mem_usage = 0.0

        # Build the NodeInfo object
        node_info = NodeInfo(
            node_name=node_name,
            cpu_capacity=cpu_capacity,
            mem_capacity=mem_capacity,
            current_cpu_usage=current_cpu_usage,
            current_mem_usage=current_mem_usage,
            network_latency={},     # Populate later if you have latency data
            network_bandwidth={}    # Populate later if you have bandwidth data
        )
        nodeinfo_list.append(node_info)

    return nodeinfo_list

def build_podinfo_objects(raw_pods: List[client.V1Pod]) -> List[PodInfo]:
    """
    Convert raw Pod objects into PodInfo. 
    For CPU/Memory requests, parse from pod.spec.containers[].resources.requests.

    Args:
        raw_pods: List of Kubernetes Pod objects.

    Returns:
        A list of PodInfo objects with relevant fields for scheduling.
    """
    podinfo_list = []

    for pod in raw_pods:
        pod_name = pod.metadata.name

        # For simplicity, sum up CPU/memory requests across all containers in the Pod
        total_cpu_req = 0.0
        total_mem_req = 0.0

        if pod.spec and pod.spec.containers:
            for container in pod.spec.containers:
                requests = container.resources.requests
                if requests:
                    # CPU
                    cpu_req_str = requests.get('cpu', '0')
                    total_cpu_req += _parse_cpu_request(cpu_req_str)
                    # Memory
                    mem_req_str = requests.get('memory', '0')
                    total_mem_req += _convert_memory_to_mebibytes(mem_req_str)

        # Suppose we store the Deployment name for reference:
        deployment_name = _extract_deployment_from_pod(pod)

        # If your system has an SLA or desired latency requirement:
        # You could store it in an annotation, or pass it in from somewhere else.
        # We'll just use a placeholder of 200 ms for now.
        sla_latency_requirement = 200.0 # can be changed as needed

        pod_info = PodInfo(
            pod_name=pod_name,
            cpu_req=total_cpu_req,
            mem_req=total_mem_req,
            sla_latency_requirement=sla_latency_requirement,
            deployment_name=deployment_name
        )
        podinfo_list.append(pod_info)

    return podinfo_list

# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def _extract_deployment_from_pod(pod: client.V1Pod) -> str:
    """
    If a pod is controlled by a ReplicaSet, which is in turn controlled by a Deployment,
    return the deployment name; otherwise return None.
    """
    if not pod.metadata.owner_references:
        return None
    apps_v1 = client.AppsV1Api()
    for owner_ref in pod.metadata.owner_references:
        if owner_ref.kind == "ReplicaSet":
            replicaset_name = owner_ref.name
            # Retrieve the replicaset to see if it references a deployment
            try:
                rs = apps_v1.read_namespaced_replica_set(replicaset_name, pod.metadata.namespace)
                if rs.metadata.owner_references:
                    for rs_owner_ref in rs.metadata.owner_references:
                        if rs_owner_ref.kind == "Deployment":
                            return rs_owner_ref.name
            except:
                pass
    return None

def _parse_cpu_request(cpu_req_str: str) -> float:
    """
    Parse CPU request strings like '250m', '1', '2.5', etc. into float cores.
    """
    if cpu_req_str.endswith('m'):
        return float(cpu_req_str[:-1]) / 1000.0
    else:
        return float(cpu_req_str)

def _convert_memory_to_mebibytes(mem_str: str) -> float:
    """
    Handle memory strings like '512Mi', '1Gi', '1000Ki', etc.
    Return a float for memory in Mi (Mebibytes).
    """
    # Common K8s notation: Ki, Mi, Gi, etc.
    # A rough approach is to parse out the numeric portion and scale accordingly.
    # For example: '512Mi' => 512, '1Gi' => 1024, '1000Ki' => 1000 / 1024 => ~0.98Mi.
    # or '2G' => might parse as 2048
    # We'll keep it simple:
    #   1 Ki = 1/1024 Mi
    #   1 Mi = 1 Mi
    #   1 Gi = 1024 Mi
    #   1 Ti = 1048576 Mi, etc.
    if not mem_str:
        return 0

    mem_str = mem_str.strip()
    number_part = ''
    unit_part = ''

    # Separate numeric from alpha characters
    for ch in mem_str:
        if ch.isdigit() or ch == '.':
            number_part += ch
        else:
            unit_part += ch

    if not number_part:
        return 0

    val = float(number_part)

    unit_part = unit_part.lower()
    if 'ki' in unit_part:
        return val / 1024.0
    elif 'mi' in unit_part:
        return val
    elif 'gi' in unit_part:
        return val * 1024.0
    elif 'ti' in unit_part:
        return val * 1024.0 * 1024.0
    elif 'k' in unit_part:  # plain 'k' might appear
        return val / 1024.0
    elif 'm' in unit_part:  # plain 'm'? Rare for memory, but let's just do a pass
        return val  # or interpret differently if you want
    elif 'g' in unit_part:
        return val * 1024.0
    # If no recognized suffix, assume it's bytes => convert to Mi
    # e.g., "524288000" bytes => ~500 Mi
    return val / (1024.0 * 1024.0)


