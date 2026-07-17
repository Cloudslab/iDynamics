# Troubleshooting

[Documentation index](index.md) | [Installation](installation.md) | [Reproducibility](reproducibility.md)

## Import Or Packaging Failures

Run package discovery first:

```bash
make discovery
```

If `idynamics` is missing, reinstall from the repository root:

```bash
python3 -m pip install -e ".[dev,analysis]"
```

If a legacy import fails, check whether the module exists under
`src/iDynamicsPackagesModules`. New code should prefer `idynamics` imports.

## Policy CLI Errors

`run_policy.py` requires either `--input` or `--demo moe`:

```bash
python3 scripts/policies/run_policy.py --policy policy4 --demo moe
```

For JSON input, validate that every pod has CPU and memory requests, every node
has capacity fields, and optional network matrices are square with the same
order as `node_names`.

`no feasible node` means all ready candidate nodes violate CPU, memory, locked
placement, or readiness constraints.

## Benchmark Fetch Problems

Third-party benchmarks are fetched into `external/benchmarks/` at pinned commits.
Check the benchmark metadata for the expected URL, commit, and local checkout:

```bash
sed -n '1,120p' benchmarks/online-boutique/metadata.yaml
```

If the checkout already exists and network access is unavailable, set:

```bash
export IDYN_SKIP_FETCH=1
```

## Namespace Rejections

Benchmark scripts intentionally reject unsafe namespaces. Use a lowercase
`idyn-*` namespace:

```bash
benchmarks/online-boutique/scripts/deploy.sh --namespace idyn-online-boutique
```

The helper refuses namespaces such as `default`, `kube-system`, `istio-system`,
and anything outside the `idyn-*` pattern.

## Kubernetes Rollout Problems

Start with resource and event inspection:

```bash
kubectl -n idyn-online-boutique get pods -o wide
kubectl -n idyn-online-boutique describe pod <pod-name>
kubectl -n idyn-online-boutique get events --sort-by=.lastTimestamp
```

Common causes are image-pull failures, insufficient node capacity, missing
storage assumptions in stateful benchmarks, or a node selector that matches no
workers.

## Mesh Telemetry Is Empty

Check that the namespace has sidecar injection enabled and that workloads have
served traffic during the query window:

```bash
kubectl get namespace idyn-online-boutique --show-labels
kubectl -n istio-system get svc prometheus
```

The sparse GDA PromQL path needs source and destination workload labels. If the
service mesh does not emit those labels for a benchmark, use adapter-level graph
metadata or captured traces instead of claiming live GDA telemetry.

## Traffic-Control Cleanup

NDM live emulation uses Linux traffic-control primitives. Run it only on testbed
nodes where you can safely reset shaping. If a run is interrupted, use the
repository cleanup helpers or your testbed's node reset procedure before starting
another network experiment.

Do not treat a generated trace as proof that qdisc state changed. Trace
providers and live mutation are separate steps.

## Artifact Validation Failures

Run:

```bash
python3 reproducibility/validate_artifacts.py
```

Then inspect the failing item folder:

```bash
sed -n '1,160p' reproducibility/items/table-v-network-trace-provider/manifest.yaml
bash reproducibility/items/table-v-network-trace-provider/run.sh --output-dir /tmp/idyn-table-v
```

If regenerated output is intentionally changed, update the expected files and
checksums together. If the claim boundary changed, update both the item manifest
and the top-level manifest.

## Live Evidence Versus Replay Evidence

If a result came from `reproducibility/items/*/run.sh`, it is data-only
regeneration unless the item manifest says otherwise. If a result came from a
benchmark smoke or load helper, it is operational evidence until the complete
run ledger and processing path are present.
