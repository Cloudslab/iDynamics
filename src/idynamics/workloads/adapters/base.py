"""External benchmark adapter metadata.

The adapters in this package intentionally describe benchmark deployment
surfaces without applying them. Cluster experiments should still go through a
run ledger and the experiment lock before invoking the generated commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EndpointSpec:
    """Public or benchmark-relevant endpoint exposed by a workload."""

    name: str
    service: str
    port: int
    protocol: str
    path: str = "/"
    notes: str = ""


@dataclass(frozen=True)
class WorkloadGeneratorSpec:
    """Workload generator entry point and tunable options."""

    name: str
    tool: str
    source_path: str
    command_template: str
    options: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class BenchmarkAdapter:
    """Static adapter contract for an external benchmark candidate."""

    key: str
    display_name: str
    priority: str
    source_url: str
    source_commit: str
    license: str
    local_path: str
    manifest_paths: tuple[str, ...]
    service_count: int
    application_services: tuple[str, ...]
    dependency_services: tuple[str, ...] = ()
    required_images: tuple[str, ...] = ()
    endpoints: tuple[EndpointSpec, ...] = ()
    workload_generators: tuple[WorkloadGeneratorSpec, ...] = ()
    resource_requirements: tuple[str, ...] = ()
    telemetry_labels: tuple[str, ...] = ()
    known_risks: tuple[str, ...] = ()
    selection_notes: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def root(self) -> Path:
        return Path(self.local_path)

    def apply_commands(self, namespace: str | None = None) -> tuple[str, ...]:
        """Return conservative kubectl apply commands for the manifest paths."""

        namespace_arg = f" -n {namespace}" if namespace else ""
        return tuple(f"kubectl apply{namespace_arg} -f {path}" for path in self.manifest_paths)

    def delete_commands(self, namespace: str | None = None) -> tuple[str, ...]:
        """Return matching kubectl delete commands for cleanup."""

        namespace_arg = f" -n {namespace}" if namespace else ""
        return tuple(f"kubectl delete{namespace_arg} -f {path} --ignore-not-found" for path in reversed(self.manifest_paths))

    def workload_command_templates(self) -> tuple[str, ...]:
        return tuple(generator.command_template for generator in self.workload_generators)
