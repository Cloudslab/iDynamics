# DeathStarBench Hotel Compatibility Adapter

This folder exposes DeathStarBench Hotel Reservation as a compatibility adapter
for iDynamics. It is not currently a first-class paper benchmark unless a fresh
stable run ledger is produced under `experiments/runs`.

## Quick Start

```bash
IDYN_NAMESPACE=idyn-dsb-hotel benchmarks/deathstar-hotel/scripts/deploy.sh
benchmarks/deathstar-hotel/scripts/smoke.sh
benchmarks/deathstar-hotel/scripts/cleanup.sh
```

The adapter expects a local DeathStarBench checkout at
`/home/ubuntu/idyn-external/deathstarbench`.

## Claim Boundary

Manual compatibility runs should be described as deployment/smoke evidence only.
Do not use this adapter for performance or generality claims without a complete
ledger containing config, commands, raw data, processed data, summary, and
paper-claim text.
