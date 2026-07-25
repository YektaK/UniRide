# Bildiri 2026 Legacy Archive

**Archive ID:** `bildiri2026_legacy`
**Created:** 2026-07-25
**Schema:** `uniride-archive/v1`

## Status

This is a **historical archive** of the original Bildiri 2026 student project material. The archived content is **non-importable and non-executable** in the current codebase.

## Evidence Classification

- **Student matrix outputs** (`results/student_matrix*`): `INVALID` — pre-distance-fix results are not current scientific evidence
- **Benchmark results and tuned parameters**: `HISTORICAL_UNVERIFIED` — valid only if independently reproduced under current contracts
- **Source code, configuration, and paper material**: `REFERENCE_ONLY` — preserved for documentation purposes

## Canonical Solver Relocation

The active GWO and HHO solvers have been relocated to `uniride_core.algorithms.tsp_matrix_metaheuristics` after exact mathematical parity verification. The canonical implementations preserve all original equations while providing truthful runtime backend reporting.

Active 2-opt, 3-opt, GA, and PSO implementations use canonical core implementations in `uniride_core.algorithms`.

## Legacy Algorithm Migration

- **B-GA** → `Core-GA-TSP` (retired name)
- **B-PSO** → `Core-PSO-TSP` (retired name)

Selection of retired identities raises an error with migration guidance.

## Manifest

The `manifest.json` file is authoritative for:
- Original repository-relative path
- Archived repository-relative path
- File size (bytes)
- SHA-256 digest
- Evidence classification

All 233 tracked files are documented in the manifest. Any unmanifested historical file in this archive directory is an anomaly.
