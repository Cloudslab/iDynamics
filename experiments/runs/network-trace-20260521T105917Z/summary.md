# network-trace-20260521T105917Z

Status: failed integration attempt

## Purpose
Initial network trace replay run.

## Result
Failed before trace generation because the experiment runner did not set the repository root on `PYTHONPATH`. The run did capture pre-run qdisc snapshots and did not apply tc impairments.

## Limitations
Superseded by completed run `network-trace-20260521T110037Z`.
