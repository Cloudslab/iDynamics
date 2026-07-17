# iDynamics Overlay Notes

MoE Serving is repository-local and CPU-only. The deploy script generates
Kubernetes Deployment and Service manifests and applies namespace labels, Istio
injection, optional worker-label placement, and iDynamics collection wrappers at
runtime.
