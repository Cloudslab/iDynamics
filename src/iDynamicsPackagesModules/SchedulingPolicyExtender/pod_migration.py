"""Portable deployment patch helpers for legacy import compatibility."""

from __future__ import annotations

from typing import Any


def patch_deployment(
    apps_v1_api: Any,
    deployment_name: str,
    namespace: str,
    new_node_name: str,
) -> bool:
    """Patch a deployment to target a node using a caller-supplied API client."""

    if not deployment_name or not namespace or not new_node_name:
        raise ValueError("deployment_name, namespace, and new_node_name are required")
    body = {
        "spec": {
            "template": {
                "spec": {
                    "nodeSelector": {
                        "kubernetes.io/hostname": new_node_name,
                    },
                },
            },
        },
    }
    apps_v1_api.patch_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=body,
    )
    return True


__all__ = ["patch_deployment"]

