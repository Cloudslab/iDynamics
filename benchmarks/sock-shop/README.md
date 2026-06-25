# Sock Shop Compatibility Adapter

Sock Shop is retained as an archived compatibility adapter. It is useful for
checking adapter plumbing against a small REST microservice application, but it
should not lead paper claims because the upstream project is deprecated.

## Quick Start

```bash
IDYN_NAMESPACE=idyn-sock-shop benchmarks/sock-shop/scripts/deploy.sh
benchmarks/sock-shop/scripts/smoke.sh
benchmarks/sock-shop/scripts/cleanup.sh
```

Expected local checkout:
`/home/ubuntu/idyn-external/sock-shop`.

## Claim Boundary

Use only as compatibility evidence unless a complete stable run ledger is
produced and the paper clearly states the deprecated upstream status.
