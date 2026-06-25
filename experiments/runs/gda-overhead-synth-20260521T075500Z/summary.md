# gda-overhead-synth-20260521T075500Z

Status: failed

## Purpose
Synthetic control-plane overhead comparison for legacy dense GDA pair scanning versus sparse active-edge construction.

## Result
- The run failed before profiling because `iDynamicsPackagesModules` was not importable when running `scripts/experiments/profile_gda_overhead.py` by path.
- The script was fixed to add the repository root to `sys.path`.

## Limitations
- No paper claims are supported by this failed run.
