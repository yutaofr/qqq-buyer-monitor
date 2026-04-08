# Recovery HMM Shadow SRD

**Status:** SHADOW RESEARCH ONLY

## Purpose

This track investigates whether an orthogonalized asymmetric HMM can release `RECOVERY`
from current suppression without modifying the live production execution chain.

## Hard Invariants

- This track must not modify the current production `target_beta` path.
- The repository production floor contract remains `target_beta >= 0.5`.
- Any execution tensor below `0.5` is research-only unless a future SRD explicitly reopens the redline.
- All outputs from this track must be written to separate research artifacts.
