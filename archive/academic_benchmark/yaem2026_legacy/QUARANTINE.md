# YAEM 2026 Legacy Evidence Quarantine

Status: historical archive; not executable evidence

This directory preserves the tracked bytes formerly located at
`academic_benchmark/yaem2026`. It is excluded from active packages, imports,
dataset discovery, benchmark execution, analysis, and current reports.

## Confirmed limitations

- Outputs derived from `student_matrix` are `INVALID` because the historical
  route construction omitted a real city from the optimized permutation.
- Historical statistical reports with invalid pairing are `INVALID`.
- Other generated results are `HISTORICAL_UNVERIFIED` unless a complete current
  provenance, fair-budget, environment, validation, and replay chain exists.
- Legacy source, configurations, presentations, and design notes are
  `REFERENCE_ONLY`; they may explain history but cannot support numerical claims.
- Historical `GWO-LKH` and `HHO-LKH` labels do not identify genuine LKH and must
  not be used by active studies.

## Permitted use

Use this archive only for provenance, design-history review, and reconstruction
of evaluated paths. Do not import its Python modules, execute its runners by
default, cite its numbers as current evidence, or relabel old results as valid.

`manifest.json` records the original path, archived path, byte size, SHA-256,
and evidence classification for each tracked source entry. A
`WITHHELD_SENSITIVE` entry intentionally has no archived path or secret content.
